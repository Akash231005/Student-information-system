"""Deterministic synthetic dataset generator for repeatable load tests."""
import argparse

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Course, CourseOffering, Student


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--students", type=int, default=1000)
    parser.add_argument("--courses", type=int, default=100)
    parser.add_argument("--offerings-per-course", type=int, default=2)
    args = parser.parse_args()
    if min(args.students, args.courses, args.offerings_per_course) < 1:
        parser.error("all counts must be positive")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing_students = set(db.scalars(select(Student.student_number).where(
            Student.student_number.like("SYN%")
        )).all())
        students = [
            Student(student_number=f"SYN{i:08d}", full_name=f"Synthetic Student {i}",
                    email=f"synthetic-{i}@example.test")
            for i in range(1, args.students + 1)
            if f"SYN{i:08d}" not in existing_students
        ]
        db.add_all(students)

        existing_codes = set(db.scalars(select(Course.course_code).where(
            Course.course_code.like("SYN%")
        )).all())
        courses = [
            Course(course_code=f"SYN{i:05d}", title=f"Synthetic Course {i}",
                   credits=2 + (i % 3))
            for i in range(1, args.courses + 1)
            if f"SYN{i:05d}" not in existing_codes
        ]
        db.add_all(courses)
        db.flush()

        all_courses = db.scalars(select(Course).where(
            Course.course_code.like("SYN%")
        ).order_by(Course.course_code)).all()
        existing_offerings = set(db.execute(select(
            CourseOffering.course_id, CourseOffering.term_code, CourseOffering.section_code
        ).where(CourseOffering.term_code == "SYNTHETIC-2026")).all())
        offerings = []
        for course in all_courses:
            for section in range(args.offerings_per_course):
                key = (course.id, "SYNTHETIC-2026", f"S{section + 1}")
                if key not in existing_offerings:
                    offerings.append(CourseOffering(
                        course_id=course.id, term_code="SYNTHETIC-2026",
                        section_code=f"S{section + 1}", capacity=30 + section * 10,
                        enrolled_count=0, status="OPEN",
                    ))
        db.add_all(offerings)
        db.commit()
        print({
            "new_students": len(students),
            "new_courses": len(courses),
            "new_offerings": len(offerings),
            "synthetic_dataset": True,
        })


if __name__ == "__main__":
    main()
