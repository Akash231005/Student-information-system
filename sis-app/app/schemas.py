from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentCreate(BaseModel):
    student_number: str = Field(min_length=1, max_length=32)
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_number: str
    full_name: str
    email: str


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255)


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=160)
    credits: int = Field(default=3, ge=1, le=12)


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_code: str
    title: str
    credits: int


class OfferingCreate(BaseModel):
    course_id: int
    term_code: str = Field(min_length=1, max_length=24)
    section_code: str = Field(min_length=1, max_length=16)
    capacity: int = Field(ge=0)
    status: str = "DRAFT"


class OfferingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int
    term_code: str
    section_code: str
    capacity: int
    enrolled_count: int
    status: str
    course: CourseOut


class EnrollmentCreate(BaseModel):
    student_id: int
    idempotency_key: str = Field(min_length=8, max_length=128)


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    offering_id: int
    status: str
    idempotency_key: str


class AttendanceCreate(BaseModel):
    student_id: int
    offering_id: int
    session_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str = Field(pattern=r"^(PRESENT|ABSENT|LATE|EXCUSED)$")

    @field_validator("session_date")
    @classmethod
    def validate_session_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class AssessmentCreate(BaseModel):
    offering_id: int
    title: str = Field(min_length=1, max_length=120)
    max_marks: float = Field(gt=0)
    assessment_date: str | None = None


class GradeCreate(BaseModel):
    student_id: int
    marks: float = Field(ge=0)


class TimetableEventCreate(BaseModel):
    offering_id: int
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    room: str = Field(min_length=1, max_length=64)
    term_code: str = Field(min_length=1, max_length=24)

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_clock_time(cls, value: str) -> str:
        time.fromisoformat(value)
        return value


class NotificationCreate(BaseModel):
    student_id: int
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=1000)
