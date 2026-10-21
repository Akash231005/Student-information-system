from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Course, CourseOffering, Student


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        student = db.scalar(select(Student).where(Student.student_number == "DEMO001"))
        if student is None:
            student = Student(
                student_number="DEMO001",
                full_name="Demo Student",
                email="demo.student@example.test",
            )
            db.add(student)

        course = db.scalar(select(Course).where(Course.course_code == "SD101"))
        if course is None:
            course = Course(course_code="SD101", title="System Design Foundations", credits=4)
            db.add(course)
            db.flush()

        offering = db.scalar(select(CourseOffering).where(
            CourseOffering.course_id == course.id,
            CourseOffering.term_code == "2026-FALL",
            CourseOffering.section_code == "A",
        ))
        if offering is None:
            offering = CourseOffering(
                course_id=course.id,
                term_code="2026-FALL",
                section_code="A",
                capacity=30,
                enrolled_count=0,
                status="OPEN",
            )
            db.add(offering)

        db.commit()
        print(f"Demo student id: {student.id}")
        print(f"Course id: {course.id}")
        print(f"Offering id: {offering.id}")


if __name__ == "__main__":
    main()
