import os
from types import SimpleNamespace

# The limiter's buckets now live in Redis and are shared between runs, so a suite that
# exercises dozens of requests would otherwise spend the same allowance a real client uses.
# Rate-limit behaviour itself is asserted directly against Redis in test_components.py.
os.environ.setdefault("SIS_RATE_LIMIT_ENABLED", "false")

import pytest
from sqlalchemy import select

from app.auth import current_account, require_staff
from app.db import SessionLocal
from app.main import app
from app.models import Student, UserAccount


@pytest.fixture(autouse=True)
def test_authorization_defaults(request):
    original = app.dependency_overrides.copy()
    staff = SimpleNamespace(id=0, student_id=0, role="STAFF")
    if request.module.__name__.endswith("test_auth"):
        # Auth tests exercise real token validation; staff routes use a real staff account.
        app.dependency_overrides.pop(current_account, None)
    else:
        # Domain tests focus on workflow invariants; auth-specific tests separately verify
        # student self-access and staff gating.
        app.dependency_overrides[current_account] = lambda: staff
        app.dependency_overrides[require_staff] = lambda: staff
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original)


def create_staff_headers(client, prefix="STAFF"):
    response = client.post("/auth/register", json={
        "student_number": f"{prefix}001",
        "full_name": "Test Staff",
        "email": f"{prefix.lower()}-{id(client)}@example.test",
        "password": "test-staff-password-long",
    })
    assert response.status_code == 201
    student_id = response.json()["student_id"]
    with SessionLocal() as db:
        account = db.scalar(select(UserAccount).where(UserAccount.student_id == student_id))
        account.role = "STAFF"
        db.commit()
        email = db.scalar(select(Student.email).where(Student.id == student_id))
    login = client.post("/auth/login", json={
        "email": email, "password": "test-staff-password-long",
    })
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
