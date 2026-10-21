from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urldefrag, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_account, ensure_student_access, require_staff
from app.components import (
    ConsistentHashRing,
    RedisTokenBucket,
    RedisTTLStore,
    UniqueIdGenerator,
    claim_worker_id,
    make_short_code,
)
from app.config import settings
from app.crawler import _is_public_https
from app.crawler import crawl as run_crawler
from app.crawlstore import CrawlStore
from app.db import get_db
from app.infra import dependency_report, get_mongo_client, get_mongo_db, get_redis
from app.models import (
    AcademicNotification,
    Assessment,
    AttendanceRecord,
    Course,
    CourseOffering,
    Enrollment,
    Grade,
    ShortLink,
    Student,
    TimetableEvent,
)
from app.schemas import (
    AssessmentCreate,
    AttendanceCreate,
    GradeCreate,
    NotificationCreate,
    TimetableEventCreate,
)
from app.shardstore import MongoShardStore

router = APIRouter()

_redis = get_redis()
rate_limiter = RedisTokenBucket(
    _redis,
    capacity=settings.rate_limit_capacity,
    refill_per_second=settings.rate_limit_refill_per_second,
)
rate_limit_metrics = {"rejections": 0}
cache = RedisTTLStore(_redis)
cache_stats = {"hits": 0, "misses": 0}
shard_store = MongoShardStore(get_mongo_client(), settings.mongo_db)
crawl_store = CrawlStore(get_mongo_db())

# Both are rebound by init_backends() once the cluster answers; nothing below this line
# touches the network at import time.
hash_ring = ConsistentHashRing()
id_generator = UniqueIdGenerator(worker_id=0)
id_metrics = {"generated": 0, "batches": 0, "collisions": 0, "last_batch_elapsed_ms": 0.0, "last_batch_ids_per_second": 0.0}
crawler_metrics = {"runs": 0, "pages_crawled": 0, "errors": 0, "elapsed_ms_total": 0.0}


def init_backends() -> dict:
    """Verify both stores, reserve this process's ID worker slot and sync the hash ring.

    Called from the application lifespan. Raises if Redis or mongos is unreachable: the
    rate-limit and cache guarantees only hold while the state is genuinely shared.
    """
    global id_generator, hash_ring
    report = dependency_report()
    id_generator = UniqueIdGenerator(worker_id=claim_worker_id(_redis))
    crawl_store.init()
    sharding = shard_store.ensure_sharded()
    hash_ring = ConsistentHashRing(shard_store.shards())
    return {"stores": report, "id_worker": id_generator.worker_id, "sharding": sharding}


@router.get("/autocomplete")
def autocomplete(q: str = Query(min_length=1, max_length=80), limit: int = Query(8, ge=1, le=20),
                 db: Session = Depends(get_db)):
    key = f"autocomplete:{q.strip().lower()}:{limit}"
    cached = cache.get(key)
    if cached is not None:
        cache_stats["hits"] += 1
        return {"items": cached, "cache": "HIT"}
    cache_stats["misses"] += 1
    term = q.strip().lower()
    rows = db.scalars(select(Course).where(
        Course.course_code.ilike(f"{term}%") | Course.title.ilike(f"{term}%")
    ).order_by(Course.course_code).limit(limit)).all()
    items = [{"id": c.id, "course_code": c.course_code, "title": c.title} for c in rows]
    cache.set(key, items, ttl_seconds=settings.cache_ttl_seconds)
    return {"items": items, "cache": "MISS"}


@router.post("/short-links", status_code=201)
def create_short_link(payload: dict, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    target = payload.get("url")
    if not isinstance(target, str) or len(target) > 2048:
        raise HTTPException(status_code=422, detail="Provide a valid URL")
    parsed = urlparse(target)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Only absolute HTTP(S) URLs are accepted")
    for _ in range(5):
        code = make_short_code(8)
        db.add(ShortLink(code=code, target_url=target))
        try:
            db.commit()
            return {"code": code, "target": target, "path": f"/s/{code}"}
        except IntegrityError:
            db.rollback()
    raise HTTPException(status_code=503, detail="Could not allocate a unique short code")


@router.get("/s/{code}")
def redirect_short_link(code: str, db: Session = Depends(get_db)):
    from fastapi.responses import RedirectResponse
    link = db.get(ShortLink, code)
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found")
    return RedirectResponse(link.target_url, status_code=307)


@router.get("/system-design/route/{key}")
def route_shard(key: str):
    predicted = hash_ring.route(key)
    actual = shard_store.owner_of(key)
    return {
        "key": key,
        "ring_prediction": predicted,
        "actual_owner": actual,
        "nodes": list(hash_ring.nodes()),
        "agrees": None if actual is None else predicted == actual,
        "note": "ring_prediction is the application hash ring; actual_owner is the shard mongos "
                "picks when it explains the query, so disagreement is visible rather than hidden.",
    }


@router.get("/system-design/ring")
def ring_info():
    return {"nodes": hash_ring.node_count(), "virtual_nodes_per_shard": hash_ring.replicas,
            "node_names": list(hash_ring.nodes()), "cluster_shards": shard_store.shards(),
            "shard_key": shard_store.shard_key()}


@router.post("/system-design/ring/nodes", status_code=201)
def add_ring_node(payload: dict, _staff=Depends(require_staff)):
    node = payload.get("node")
    if not isinstance(node, str) or not node.strip() or len(node) > 64:
        raise HTTPException(status_code=422, detail="node must be a non-empty string of at most 64 chars")
    before = hash_ring.node_count()
    hash_ring.add_node(node)
    return {"nodes_before": before, "nodes_after": hash_ring.node_count(),
            "added": hash_ring.node_count() > before,
            "note": "Ring membership only. Registering a real shard with mongos is a separate "
                    "cluster operation (docs/DEMO_RUNBOOK.md); chunks then move via "
                    "/system-design/shards/rebalance."}


@router.delete("/system-design/ring/nodes/{node}")
def remove_ring_node(node: str, _staff=Depends(require_staff)):
    before = hash_ring.node_count()
    hash_ring.remove_node(node)
    if before == hash_ring.node_count():
        raise HTTPException(status_code=404, detail="Shard node not found")
    return {"nodes_before": before, "nodes_after": hash_ring.node_count(), "removed": node}


@router.get("/system-design/ids")
def generate_ids(count: int = Query(1, ge=1, le=1000)):
    started = perf_counter()
    values = [id_generator.next_id() for _ in range(count)]
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    collisions = len(values) - len(set(values))
    id_metrics["generated"] += len(values)
    id_metrics["batches"] += 1
    id_metrics["collisions"] += collisions
    id_metrics["last_batch_elapsed_ms"] = elapsed_ms
    id_metrics["last_batch_ids_per_second"] = round(count / max(elapsed_ms / 1000, 0.000001), 2)
    # 64-bit identifiers exceed JavaScript's exact integer range; serialize them as strings
    # so clients do not round distinct IDs to the same Number value.
    return {"ids": [str(value) for value in values], "count": len(values), "unique_in_batch": collisions == 0,
            "elapsed_ms": elapsed_ms, "ids_per_second": id_metrics["last_batch_ids_per_second"],
            "generated_total": id_metrics["generated"], "collisions_total": id_metrics["collisions"]}


@router.get("/system-design/metrics")
def component_metrics(db: Session = Depends(get_db)):
    short_link_count = db.scalar(select(func.count()).select_from(ShortLink)) or 0
    return {
        "rate_limiter": {"algorithm": "token bucket in Redis (atomic Lua)",
                         "capacity": rate_limiter.capacity,
                         "refill_per_second": rate_limiter.refill_rate,
                         "rejections": rate_limit_metrics["rejections"],
                         "scope": "shared by every app process",
                         "active_buckets": rate_limiter.tracked_keys()},
        "key_value_store": {"type": "Redis TTL cache, server-side expiry",
                            "ttl_seconds": settings.cache_ttl_seconds,
                            "items": cache.item_count(), **cache.eviction_policy(), **cache_stats},
        "consistent_hashing": {"nodes": list(hash_ring.nodes()),
                                "virtual_nodes_per_node": hash_ring.replicas},
        "id_generator": {"algorithm": "time-sortable 64-bit",
                         "scope": "worker id reserved in Redis",
                         "worker_id": id_generator.worker_id, **id_metrics},
        "url_shortener": {"persisted_links": short_link_count, "redirect_status": 307},
        "sharding": {**shard_store.cluster_health(), **shard_store.distribution()},
        "crawler": {**crawler_metrics, "store": crawl_store.stats(),
                    "average_pages_per_second": round(
                        crawler_metrics["pages_crawled"] / max(crawler_metrics["elapsed_ms_total"] / 1000, 0.001), 2
                    )},
        "autocomplete_cache_ttl_seconds": settings.cache_ttl_seconds,
    }


@router.post("/attendance", status_code=201)
def record_attendance(payload: AttendanceCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    offering = db.get(CourseOffering, payload.offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail="Offering not found")
    is_enrolled = db.scalar(select(Enrollment.id).where(
        and_(Enrollment.student_id == payload.student_id,
             Enrollment.offering_id == payload.offering_id,
             Enrollment.status == "ENROLLED")
    ))
    if is_enrolled is None:
        raise HTTPException(status_code=409, detail="Attendance requires an active enrollment")
    record = AttendanceRecord(**payload.model_dump())
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Attendance already recorded for this session") from exc
    return {"id": record.id, "student_id": record.student_id, "offering_id": record.offering_id,
            "session_date": record.session_date, "status": record.status}


@router.get("/attendance")
def list_attendance(student_id: int | None = None, offering_id: int | None = None,
                    db: Session = Depends(get_db), _staff=Depends(require_staff)):
    stmt = select(AttendanceRecord).order_by(AttendanceRecord.session_date.desc())
    if student_id is not None:
        stmt = stmt.where(AttendanceRecord.student_id == student_id)
    if offering_id is not None:
        stmt = stmt.where(AttendanceRecord.offering_id == offering_id)
    return [{"id": r.id, "student_id": r.student_id, "offering_id": r.offering_id,
             "session_date": r.session_date, "status": r.status}
            for r in db.scalars(stmt.limit(500)).all()]


@router.post("/assessments", status_code=201)
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    if db.get(CourseOffering, payload.offering_id) is None:
        raise HTTPException(status_code=404, detail="Offering not found")
    row = Assessment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, **payload.model_dump()}


@router.post("/assessments/{assessment_id}/grades", status_code=201)
def upsert_grade(assessment_id: int, payload: GradeCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if payload.marks > assessment.max_marks:
        raise HTTPException(status_code=422, detail=f"Marks cannot exceed {assessment.max_marks}")
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    is_enrolled = db.scalar(select(Enrollment.id).where(
        and_(Enrollment.student_id == payload.student_id,
             Enrollment.offering_id == assessment.offering_id,
             Enrollment.status == "ENROLLED")
    ))
    if is_enrolled is None:
        raise HTTPException(status_code=409, detail="Grades can only be recorded for enrolled students")
    grade = db.scalar(select(Grade).where(
        Grade.assessment_id == assessment_id, Grade.student_id == payload.student_id
    ))
    if grade is None:
        grade = Grade(assessment_id=assessment_id, student_id=payload.student_id, marks=payload.marks)
        db.add(grade)
    else:
        grade.marks = payload.marks
        grade.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(grade)
    return {"id": grade.id, "assessment_id": grade.assessment_id,
            "student_id": grade.student_id, "marks": grade.marks}


@router.get("/students/{student_id}/grades")
def student_grades(student_id: int, db: Session = Depends(get_db), account=Depends(current_account)):
    ensure_student_access(student_id, account)
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    rows = db.execute(
        select(Grade, Assessment).join(Assessment, Grade.assessment_id == Assessment.id)
        .where(Grade.student_id == student_id).order_by(Assessment.assessment_date, Assessment.id)
    ).all()
    return [{"assessment_id": a.id, "title": a.title, "max_marks": a.max_marks,
             "marks": g.marks, "date": a.assessment_date} for g, a in rows]


@router.post("/timetable", status_code=201)
def create_timetable_event(payload: TimetableEventCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    if db.get(CourseOffering, payload.offering_id) is None:
        raise HTTPException(status_code=404, detail="Offering not found")
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=422, detail="end_time must be later than start_time")
    conflict = db.scalar(select(TimetableEvent.id).where(
        TimetableEvent.term_code == payload.term_code,
        TimetableEvent.day_of_week == payload.day_of_week,
        TimetableEvent.room == payload.room,
        TimetableEvent.start_time < payload.end_time,
        TimetableEvent.end_time > payload.start_time,
    ))
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Room already has an overlapping event")
    event = TimetableEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, **payload.model_dump()}


@router.get("/timetable")
def get_timetable(term: str = Query(min_length=1, max_length=24), db: Session = Depends(get_db)):
    rows = db.execute(
        select(TimetableEvent, CourseOffering, Course)
        .join(CourseOffering, TimetableEvent.offering_id == CourseOffering.id)
        .join(Course, CourseOffering.course_id == Course.id)
        .where(TimetableEvent.term_code == term)
        .order_by(TimetableEvent.day_of_week, TimetableEvent.start_time)
    ).all()
    return [{"id": e.id, "course_code": c.course_code, "title": c.title,
             "day_of_week": e.day_of_week, "start_time": e.start_time,
             "end_time": e.end_time, "room": e.room, "term_code": e.term_code}
            for e, o, c in rows]


@router.post("/notifications", status_code=201)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    item = AcademicNotification(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "student_id": item.student_id, "title": item.title,
            "message": item.message, "created_at": item.created_at}


@router.get("/students/{student_id}/notifications")
def list_notifications(student_id: int, db: Session = Depends(get_db), account=Depends(current_account)):
    ensure_student_access(student_id, account)
    ensure_student_access(student_id, account)
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    rows = db.scalars(select(AcademicNotification).where(
        AcademicNotification.student_id == student_id
    ).order_by(AcademicNotification.created_at.desc()).limit(100)).all()
    return [{"id": n.id, "title": n.title, "message": n.message,
             "read_at": n.read_at, "created_at": n.created_at} for n in rows]


@router.post("/system-design/crawler/submit", status_code=202)
def crawler_submit(payload: dict, _staff=Depends(require_staff)):
    """Queue public HTTPS URLs in the durable MongoDB frontier for the next crawl run."""
    urls = payload.get("urls", [])
    if not isinstance(urls, list) or len(urls) > 100:
        raise HTTPException(status_code=422, detail="urls must be a list of at most 100 URLs")
    accepted = []
    rejected = []
    for value in urls:
        if not isinstance(value, str) or len(value) > 2048:
            rejected.append({"url": str(value)[:100], "reason": "invalid URL"})
            continue
        if not _is_public_https(value):
            rejected.append({"url": value, "reason": "only public credential-free HTTPS URLs accepted"})
            continue
        url = urldefrag(value)[0]
        crawl_store.enqueue([(url, 0)], url)
        accepted.append(url)
    return {"accepted": accepted, "rejected": rejected,
            "frontier_pending": crawl_store.pending_count(),
            "note": "Queued in MongoDB under each URL as its own seed. A run against that seed "
                    "consumes the queue and skips anything already stored."}


# Sharded records live in MongoDB behind mongos; the shard key is the record key itself.
@router.put("/system-design/sharded-records/{key}")
def put_sharded_record(key: str, payload: dict, _staff=Depends(require_staff)):
    return shard_store.put(key, payload)


@router.get("/system-design/sharded-records/{key}")
def get_sharded_record(key: str):
    value = shard_store.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "shard": shard_store.owner_of(key), "value": value}


@router.get("/system-design/sharded-records")
def shard_distribution():
    distribution = shard_store.distribution()
    predicted = hash_ring.ownership(shard_store.key_range(limit=500))
    return {
        "distribution": distribution,
        "ring_prediction": predicted,
        "note": "distribution counts come from the cluster (collStats plus config.chunks); "
                "ring_prediction is what the application ring would have chosen.",
    }


@router.get("/system-design/shards")
def shard_cluster_health():
    return shard_store.cluster_health()


@router.post("/system-design/shards/rebalance")
def shard_rebalance(_staff=Depends(require_staff)):
    return shard_store.rebalance()


@router.post("/system-design/shards/move-chunk")
def shard_move_chunk(payload: dict, _staff=Depends(require_staff)):
    to_shard = payload.get("to_shard")
    from_shard = payload.get("from_shard")
    if not isinstance(to_shard, str):
        raise HTTPException(status_code=422, detail="to_shard is required")
    if from_shard is not None and not isinstance(from_shard, str):
        raise HTTPException(status_code=422, detail="from_shard must be a string when given")
    try:
        return shard_store.move_chunk(to_shard, from_shard=from_shard)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/system-design/crawler/run")
def run_web_crawler(payload: dict, _staff=Depends(require_staff)):
    seed = payload.get("seed_url")
    max_pages = payload.get("max_pages", 10)
    if not isinstance(seed, str):
        raise HTTPException(status_code=422, detail="seed_url is required")
    if not isinstance(max_pages, int) or not 1 <= max_pages <= 20:
        raise HTTPException(status_code=422, detail="max_pages must be between 1 and 20")
    try:
        result = run_crawler(seed, max_pages=max_pages, store=crawl_store)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    crawler_metrics["runs"] += 1
    crawler_metrics["pages_crawled"] += result["pages_crawled"]
    crawler_metrics["errors"] += len(result["errors"])
    crawler_metrics["elapsed_ms_total"] += result["elapsed_ms"]
    return result


@router.get("/system-design/crawler/state")
def crawler_state(limit: int = Query(25, ge=1, le=100)):
    return {**crawl_store.stats(), "recent_pages": crawl_store.recent_pages(limit)}

@router.post("/enrollments/{enrollment_id}/drop")
def drop_enrollment(enrollment_id: int, db: Session = Depends(get_db), account=Depends(current_account)):
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    ensure_student_access(enrollment.student_id, account)
    if enrollment.status != "ENROLLED":
        raise HTTPException(status_code=409, detail="Enrollment is not active")
    # Both changes commit atomically; a retry cannot decrement twice because the status
    # transition is conditional on ENROLLED.
    changed = db.execute(
        update(Enrollment)
        .where(Enrollment.id == enrollment_id, Enrollment.status == "ENROLLED")
        .values(status="DROPPED")
        .returning(Enrollment.id)
    ).scalar()
    if changed is None:
        db.rollback()
        raise HTTPException(status_code=409, detail="Enrollment is not active")
    counters = db.execute(
        update(CourseOffering)
        .where(CourseOffering.id == enrollment.offering_id, CourseOffering.enrolled_count > 0)
        .values(enrolled_count=CourseOffering.enrolled_count - 1)
        .returning(CourseOffering.capacity, CourseOffering.enrolled_count)
    ).first()
    if counters is None:
        db.rollback()
        raise HTTPException(status_code=500, detail="Enrollment counter invariant failed")
    capacity, enrolled_count = counters
    db.commit()
    return {"enrollment_id": enrollment_id, "status": "DROPPED",
            "remaining_seats": capacity - enrolled_count}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), account=Depends(current_account)):
    notification = db.get(AcademicNotification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    ensure_student_access(notification.student_id, account)
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
    return {"id": notification.id, "read_at": notification.read_at}

@router.post("/system-design/ring/experiment")
def ring_movement_experiment(
    node: str = Query(default="shard-c", min_length=1, max_length=64),
    key_count: int = Query(default=1000, ge=10, le=10000),
    migrate: bool = Query(default=False),
    _staff=Depends(require_staff),
):
    """Add a node to the ring and report how many keys the ring would move.

    With `migrate=true` the cluster is asked to make that real: chunks are migrated until
    every registered shard holds an even share, then stored keys are re-read to prove no
    record was lost.
    """
    keys = [f"synthetic-key-{i}" for i in range(key_count)]
    simulation = ConsistentHashRing(list(hash_ring.nodes()), replicas=hash_ring.replicas)
    before = {key: simulation.route(key) for key in keys}
    old_nodes = simulation.node_count()
    simulation.add_node(node)
    moved = sum(before[key] != simulation.route(key) for key in keys)

    result = {
        "keys_sampled": key_count,
        "nodes_before": old_nodes,
        "nodes_after": simulation.node_count(),
        "node_added": simulation.node_count() > old_nodes,
        "keys_rerouted": moved,
        "rerouted_fraction": moved / key_count,
    }
    if migrate and shard_store.is_sharded():
        stored = shard_store.key_range(limit=200)
        result["chunk_migration"] = shard_store.rebalance()
        result["keys_still_readable"] = sum(1 for key in stored if shard_store.get(key) is not None)
        result["keys_checked"] = len(stored)
    else:
        result["note"] = (
            "Ring membership updated only. Pass migrate=true to move real chunks with the "
            "cluster balancer, or use /system-design/shards/move-chunk for one explicit move."
        )
    return result
