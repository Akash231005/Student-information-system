from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_account, ensure_student_access, require_staff
from app.components import (
    ConsistentHashRing,
    TokenBucketRateLimiter,
    TTLKeyValueStore,
    UniqueIdGenerator,
    make_short_code,
)
from app.config import settings
from app.db import get_db
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

router = APIRouter()
rate_limiter = TokenBucketRateLimiter(capacity=120, refill_per_second=10)
rate_limit_metrics = {"rejections": 0}
cache = TTLKeyValueStore(max_items=500)
CACHE_ENABLED = settings.cache_enabled
cache_stats = {"hits": 0, "misses": 0}
hash_ring = ConsistentHashRing(["shard-a", "shard-b", "shard-c"])
id_generator = UniqueIdGenerator(worker_id=1)
id_metrics = {"generated": 0, "batches": 0, "collisions": 0, "last_batch_elapsed_ms": 0.0, "last_batch_ids_per_second": 0.0}
crawler_metrics = {"runs": 0, "pages_crawled": 0, "errors": 0, "elapsed_ms_total": 0.0}
crawler_seen: set[str] = set()


@router.get("/autocomplete")
def autocomplete(q: str = Query(min_length=1, max_length=80), limit: int = Query(8, ge=1, le=20),
                 db: Session = Depends(get_db)):
    key = f"autocomplete:{q.strip().lower()}:{limit}"
    if CACHE_ENABLED:
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
    if CACHE_ENABLED:
        cache.set(key, items, ttl_seconds=20)
        return {"items": items, "cache": "MISS"}
    return {"items": items, "cache": "DISABLED"}


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
    return {"key": key, "shard": hash_ring.route(key), "nodes": hash_ring.node_count(),
            "note": "Routing demonstration only; no data migration or replication is performed."}


@router.get("/system-design/ring")
def ring_info():
    return {"nodes": hash_ring.node_count(), "virtual_nodes_per_shard": hash_ring.replicas}


@router.post("/system-design/ring/nodes", status_code=201)
def add_ring_node(payload: dict, _staff=Depends(require_staff)):
    node = payload.get("node")
    if not isinstance(node, str) or not node.strip() or len(node) > 64:
        raise HTTPException(status_code=422, detail="node must be a non-empty string of at most 64 chars")
    before = hash_ring.node_count()
    hash_ring.add_node(node)
    return {"nodes_before": before, "nodes_after": hash_ring.node_count(),
            "added": hash_ring.node_count() > before}


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
        "rate_limiter": {"algorithm": "token bucket", "capacity": rate_limiter.capacity,
                         "refill_per_second": rate_limiter.refill_rate,
                         "rejections": rate_limit_metrics["rejections"], "scope": "single process"},
        "key_value_store": {"type": "bounded TTL + LRU", "enabled": CACHE_ENABLED,
                            "items": len(cache._items), **cache_stats},
        "consistent_hashing": {"nodes": list(hash_ring.nodes()),
                                "virtual_nodes_per_node": hash_ring.replicas},
        "id_generator": {"algorithm": "time-sortable 64-bit", "scope": "single worker",
                         **id_metrics},
        "url_shortener": {"persisted_links": short_link_count, "redirect_status": 307},
        "crawler": {**crawler_metrics,
                    "average_pages_per_second": round(
                        crawler_metrics["pages_crawled"] / max(crawler_metrics["elapsed_ms_total"] / 1000, 0.001), 2
                    )},
        "autocomplete_cache_ttl_seconds": 20,
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


@router.post("/system-design/crawler/submit")
def crawler_submit(payload: dict, _staff=Depends(require_staff)):
    """Bounded synthetic crawler queue: accepts URLs but does not fetch arbitrary network targets."""
    urls = payload.get("urls", [])
    if not isinstance(urls, list) or len(urls) > 100:
        raise HTTPException(status_code=422, detail="urls must be a list of at most 100 URLs")
    accepted = []
    rejected = []
    for value in urls:
        if not isinstance(value, str) or len(value) > 2048:
            rejected.append({"url": str(value)[:100], "reason": "invalid URL"})
            continue
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            rejected.append({"url": value, "reason": "only credential-free HTTPS URLs accepted"})
            continue
        if value not in crawler_seen:
            crawler_seen.add(value)
            accepted.append(value)
    return {"accepted": accepted, "rejected": rejected, "unique_seen": len(crawler_seen),
            "note": "This prototype tracks a crawl frontier only; it does not fetch or parse pages yet."}

# Experimental shard-local key/value data. This is deliberately separate from authoritative
# academic records; it demonstrates routing and movement, not PostgreSQL horizontal scaling.
shard_data: dict[str, dict[str, dict]] = {node: {} for node in ["shard-a", "shard-b", "shard-c"]}


@router.put("/system-design/sharded-records/{key}")
def put_sharded_record(key: str, payload: dict, _staff=Depends(require_staff)):
    node = hash_ring.route(key)
    if node is None:
        raise HTTPException(status_code=503, detail="No shard nodes available")
    shard_data.setdefault(node, {})[key] = payload
    return {"key": key, "shard": node, "stored": True}


@router.get("/system-design/sharded-records/{key}")
def get_sharded_record(key: str):
    node = hash_ring.route(key)
    if node is None:
        raise HTTPException(status_code=503, detail="No shard nodes available")
    value = shard_data.get(node, {}).get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found on its routed shard")
    return {"key": key, "shard": node, "value": value}


@router.get("/system-design/sharded-records")
def shard_distribution():
    counts = {node: len(shard_data.get(node, {})) for node in hash_ring.nodes()}
    orphaned = {node: len(records) for node, records in shard_data.items() if node not in hash_ring.nodes() and records}
    return {"counts": counts, "orphaned_records_by_removed_node": orphaned,
            "total_records": sum(counts.values()) + sum(orphaned.values()),
            "warning": "In-memory demo data is lost on restart; node removal does not migrate records."}

from app.crawler import crawl as run_crawler


@router.post("/system-design/crawler/run")
def run_web_crawler(payload: dict, _staff=Depends(require_staff)):
    seed = payload.get("seed_url")
    max_pages = payload.get("max_pages", 10)
    if not isinstance(seed, str):
        raise HTTPException(status_code=422, detail="seed_url is required")
    if not isinstance(max_pages, int) or not 1 <= max_pages <= 20:
        raise HTTPException(status_code=422, detail="max_pages must be between 1 and 20")
    try:
        result = run_crawler(seed, max_pages=max_pages)
        crawler_metrics["runs"] += 1
        crawler_metrics["pages_crawled"] += result["pages_crawled"]
        crawler_metrics["errors"] += len(result["errors"])
        crawler_metrics["elapsed_ms_total"] += result["elapsed_ms"]
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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
    node: str = Query(default="shard-d", min_length=1, max_length=64),
    key_count: int = Query(default=1000, ge=10, le=10000),
    _staff=Depends(require_staff),
):
    keys = [f"synthetic-key-{i}" for i in range(key_count)]
    simulation = ConsistentHashRing(list(hash_ring.nodes()), replicas=hash_ring.replicas)
    before = {key: simulation.route(key) for key in keys}
    old_nodes = simulation.node_count()
    simulation.add_node(node)
    after = {key: simulation.route(key) for key in keys}
    moved = sum(before[key] != after[key] for key in keys)
    return {
        "keys_sampled": key_count,
        "nodes_before": old_nodes,
        "nodes_after": simulation.node_count(),
        "node_added": simulation.node_count() > old_nodes,
        "keys_moved": moved,
        "moved_fraction": moved / key_count,
        "warning": "Simulation only: routing changed; stored shard data was not migrated.",
    }
