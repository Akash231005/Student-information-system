"""Create or promote a staff account for local demonstrations.

Example: uv run python -m scripts.create_staff --email staff@example.test
The password is read interactively unless --password is supplied.
"""
import argparse
from getpass import getpass

from sqlalchemy import select

from app.auth import hash_password
from app.db import Base, SessionLocal, engine
from app.models import Student, UserAccount


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--student-number", default="STAFF001")
    parser.add_argument("--name", default="SIS Staff")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="Avoid this option on shared systems; prompt is safer.")
    args = parser.parse_args()
    password = args.password or getpass("Staff password (minimum 10 characters): ")
    if len(password) < 10:
        parser.error("password must contain at least 10 characters")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        student = db.scalar(select(Student).where(Student.email == args.email.lower().strip()))
        if student is None:
            student = Student(student_number=args.student_number, full_name=args.name,
                              email=args.email.lower().strip())
            db.add(student)
            db.flush()
        account = db.scalar(select(UserAccount).where(UserAccount.student_id == student.id))
        if account is None:
            account = UserAccount(student_id=student.id, password_hash=hash_password(password), role="STAFF")
            db.add(account)
        else:
            account.password_hash = hash_password(password)
            account.role = "STAFF"
        db.commit()
        print(f"Staff account ready: {student.email} (student id {student.id})")


if __name__ == "__main__":
    main()
