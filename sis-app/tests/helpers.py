from app.auth import issue_token
from app.db import SessionLocal
from app.models import Student, UserAccount


def staff_headers() -> dict[str, str]:
    """Create an isolated staff principal for API integration tests."""
    with SessionLocal() as db:
        student = Student(
            student_number="TEST-STAFF",
            full_name="Test Staff",
            email="test-staff@example.test",
        )
        db.add(student)
        db.flush()
        account = UserAccount(student_id=student.id, password_hash="test-only", role="STAFF")
        db.add(account)
        db.commit()
        db.refresh(account)
        token = issue_token(account)
    return {"Authorization": f"Bearer {token}"}
