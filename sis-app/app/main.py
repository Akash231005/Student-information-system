from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import current_account, ensure_student_access, require_staff
from app.config import settings
from app.db import get_db
from app.extended import cache, init_backends, rate_limit_metrics, rate_limiter
from app.extended import router as extended_router
from app.infra import dependency_report
from app.models import Course, CourseOffering, Enrollment, Student
from app.schemas import (
    CourseCreate,
    CourseOut,
    EnrollmentCreate,
    EnrollmentOut,
    OfferingCreate,
    OfferingOut,
    StudentCreate,
    StudentOut,
    StudentUpdate,
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Refuses to start when Redis or mongos is down: shared state is the whole point of
    # these components, so a silent per-process fallback would falsify their guarantees.
    # Clients are process-wide and closed at interpreter exit (see app.infra), so an
    # in-process restart - such as a test client context - keeps them usable.
    application.state.startup = init_backends()
    yield


app = FastAPI(title="SIS Scalability Lab", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(extended_router)


@app.get("/health")
def health():
    try:
        report = dependency_report()
    except RuntimeError as exc:
        return JSONResponse(
            status_code=503, content={"status": "degraded", "detail": str(exc)}
        )
    return {"status": "ok", "database": "postgresql", "stores": report}


@app.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    student = Student(**payload.model_dump())
    db.add(student)
    try:
        db.commit()
        db.refresh(student)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Student number or email already exists") from exc
    return student


@app.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db), account=Depends(current_account)):
    ensure_student_access(student_id, account)
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.patch("/students/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    account=Depends(current_account),
):
    ensure_student_access(student_id, account)
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    changes = {key: value for key, value in payload.model_dump(exclude_unset=True).items()
               if value is not None}
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one profile field to update")
    if "email" in changes:
        changes["email"] = changes["email"].lower().strip()
    for key, value in changes.items():
        setattr(student, key, value)
    try:
        db.commit()
        db.refresh(student)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    return student


@app.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    course = Course(**payload.model_dump())
    db.add(course)
    try:
        db.commit()
        db.refresh(course)
        cache.invalidate_prefix("autocomplete:")
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Course code already exists") from exc
    return course


@app.get("/courses", response_model=list[CourseOut])
def search_courses(
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Course).order_by(Course.course_code).limit(limit)
    if q:
        term = q.strip().lower()
        stmt = select(Course).where(
            Course.course_code.ilike(f"%{term}%") | Course.title.ilike(f"%{term}%")
        ).order_by(Course.course_code).limit(limit)
    return list(db.scalars(stmt).all())


@app.post("/offerings", response_model=OfferingOut, status_code=status.HTTP_201_CREATED)
def create_offering(payload: OfferingCreate, db: Session = Depends(get_db), _staff=Depends(require_staff)):
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if payload.status not in {"DRAFT", "OPEN", "CLOSED", "CANCELLED"}:
        raise HTTPException(status_code=422, detail="Invalid offering status")
    offering = CourseOffering(**payload.model_dump())
    db.add(offering)
    try:
        db.commit()
        db.refresh(offering)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Offering section already exists") from exc
    return db.scalar(
        select(CourseOffering).options(joinedload(CourseOffering.course))
        .where(CourseOffering.id == offering.id)
    )


@app.get("/offerings", response_model=list[OfferingOut])
def list_offerings(
    term: str | None = None,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(CourseOffering).options(joinedload(CourseOffering.course)).order_by(CourseOffering.id)
    if term:
        stmt = stmt.where(CourseOffering.term_code == term)
    if q:
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.join(CourseOffering.course).where(
            Course.course_code.ilike(pattern) | Course.title.ilike(pattern)
        )
    return list(db.scalars(stmt.limit(limit)).unique().all())


@app.post("/offerings/{offering_id}/enroll", response_model=EnrollmentOut, status_code=201)
def enroll(offering_id: int, payload: EnrollmentCreate, db: Session = Depends(get_db), account=Depends(current_account)):
    ensure_student_access(payload.student_id, account)
    # PostgreSQL performs the seat reservation atomically. The conditional update prevents
    # two transactions from consuming the same final seat. Enrollment insert shares the
    # transaction, so a failed insert rolls back the seat reservation.
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    existing_key = db.scalar(select(Enrollment).where(
        Enrollment.idempotency_key == payload.idempotency_key
    ))
    if existing_key:
        if existing_key.student_id == payload.student_id and existing_key.offering_id == offering_id:
            return existing_key
        raise HTTPException(status_code=409, detail="Idempotency key already used for another request")

    stmt = (
        update(CourseOffering)
        .where(
            CourseOffering.id == offering_id,
            CourseOffering.status == "OPEN",
            CourseOffering.enrolled_count < CourseOffering.capacity,
        )
        .values(enrolled_count=CourseOffering.enrolled_count + 1)
        .returning(CourseOffering.id)
    )
    reserved = db.scalar(stmt)
    if reserved is None:
        offering = db.get(CourseOffering, offering_id)
        if offering is None:
            raise HTTPException(status_code=404, detail="Offering not found")
        if offering.status != "OPEN":
            raise HTTPException(status_code=409, detail="Registration is not open")
        raise HTTPException(status_code=409, detail="Offering is full")

    enrollment = Enrollment(
        student_id=payload.student_id,
        offering_id=offering_id,
        idempotency_key=payload.idempotency_key,
        status="ENROLLED",
    )
    db.add(enrollment)
    try:
        db.commit()
        db.refresh(enrollment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate enrollment or idempotency key") from exc
    return enrollment


@app.get("/students/{student_id}/enrollments", response_model=list[EnrollmentOut])
def student_enrollments(student_id: int, db: Session = Depends(get_db), account=Depends(current_account)):
    ensure_student_access(student_id, account)
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    stmt = select(Enrollment).where(
        Enrollment.student_id == student_id,
        Enrollment.status == "ENROLLED",
    ).order_by(Enrollment.id)
    return list(db.scalars(stmt).all())

# Process-local counters are for the lab dashboard; the rate-limit *decisions* are shared
# through Redis, so the limiter itself is cluster-wide even though these counters are not.
import time

RATE_LIMIT_ENABLED = settings.rate_limit_enabled
api_limiter = rate_limiter
http_metrics = {"requests": 0, "errors": 0, "rate_limited": 0, "latency_ms": []}


@app.middleware("http")
async def apply_api_rate_limit(request: Request, call_next):
    started = time.perf_counter()
    client = request.client.host if request.client else "unknown"
    group = request.url.path.strip("/").split("/")[0] or "root"
    if (
        RATE_LIMIT_ENABLED
        and request.url.path not in {"/health", "/openapi.json", "/docs", "/redoc"}
        and not api_limiter.allow(f"{client}:{group}")
    ):
        http_metrics["requests"] += 1
        http_metrics["errors"] += 1
        http_metrics["rate_limited"] += 1
        rate_limit_metrics["rejections"] += 1
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "1"},
        )
    response = await call_next(request)
    elapsed = (time.perf_counter() - started) * 1000
    http_metrics["requests"] += 1
    if response.status_code >= 400:
        http_metrics["errors"] += 1
    http_metrics["latency_ms"].append(round(elapsed, 3))
    if len(http_metrics["latency_ms"]) > 5000:
        del http_metrics["latency_ms"][:1000]
    return response


@app.get("/system-design/http-metrics")
def get_http_metrics():
    values = sorted(http_metrics["latency_ms"])
    def percentile(p):
        if not values:
            return None
        return values[min(len(values) - 1, int((len(values) - 1) * p))]
    return {
        "requests_seen": http_metrics["requests"],
        "error_responses": http_metrics["errors"],
        "rate_limited": http_metrics["rate_limited"],
        "sample_count": len(values),
        "latency_ms": {"p50": percentile(0.50), "p95": percentile(0.95), "p99": percentile(0.99)},
        "scope": "single-process in-memory counters; reset on restart",
    }

from app.auth import router as auth_router

app.include_router(auth_router)

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB_ROOT = Path(__file__).resolve().parent.parent
WEB_INDEX = WEB_ROOT / "web" / "index.html"
WEB_DIST = WEB_ROOT / "frontend" / "dist"

# Production frontend is the compiled React app; retain the previous page as a safe
# fallback until the frontend bundle has been built on a fresh checkout.
if (WEB_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="frontend-assets")


@app.get("/", include_in_schema=False)
def dashboard():
    react_index = WEB_DIST / "index.html"
    return FileResponse(react_index if react_index.is_file() else WEB_INDEX)


# Let Vite's public assets (favicon, etc.) resolve from the compiled bundle root.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST), name="frontend-public-assets")
