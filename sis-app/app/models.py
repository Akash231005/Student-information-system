from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    credits: Mapped[int] = mapped_column(Integer, default=3)
    offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="course")


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_offering_capacity_nonnegative"),
        CheckConstraint("enrolled_count >= 0", name="ck_offering_count_nonnegative"),
        CheckConstraint("enrolled_count <= capacity", name="ck_offering_count_within_capacity"),
        UniqueConstraint("course_id", "term_code", "section_code", name="uq_offering_term_section"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    term_code: Mapped[str] = mapped_column(String(24), index=True)
    section_code: Mapped[str] = mapped_column(String(16))
    capacity: Mapped[int] = mapped_column(Integer)
    enrolled_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    course: Mapped[Course] = relationship(back_populates="offerings")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="offering")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        Index(
            "uq_active_student_offering", "student_id", "offering_id", unique=True,
            postgresql_where=text("status = 'ENROLLED'"),
            sqlite_where=text("status = 'ENROLLED'"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    offering_id: Mapped[int] = mapped_column(ForeignKey("course_offerings.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="ENROLLED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    student: Mapped[Student] = relationship(back_populates="enrollments")
    offering: Mapped[CourseOffering] = relationship(back_populates="enrollments")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("student_id", "offering_id", "session_date", name="uq_attendance_session"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    offering_id: Mapped[int] = mapped_column(ForeignKey("course_offerings.id"), index=True)
    session_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(12))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (CheckConstraint("max_marks > 0", name="ck_assessment_max_marks_positive"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    offering_id: Mapped[int] = mapped_column(ForeignKey("course_offerings.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    max_marks: Mapped[float] = mapped_column()
    assessment_date: Mapped[str | None] = mapped_column(String(10), nullable=True)


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id", name="uq_grade_assessment_student"),
        CheckConstraint("marks >= 0", name="ck_grade_marks_nonnegative"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    marks: Mapped[float] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TimetableEvent(Base):
    __tablename__ = "timetable_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    offering_id: Mapped[int] = mapped_column(ForeignKey("course_offerings.id"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    room: Mapped[str] = mapped_column(String(64))
    term_code: Mapped[str] = mapped_column(String(24), index=True)


class AcademicNotification(Base):
    __tablename__ = "academic_notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(String(1000))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ShortLink(Base):
    __tablename__ = "short_links"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    target_url: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserAccount(Base):
    __tablename__ = "user_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="STUDENT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
