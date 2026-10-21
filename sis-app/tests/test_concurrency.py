import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

# This test is intentionally opt-in because SQLite cannot prove PostgreSQL concurrency semantics.
if not os.getenv("DATABASE_URL", "").startswith("postgresql"):
    pytest.skip("Set DATABASE_URL to a dedicated PostgreSQL test database", allow_module_level=True)

from app.db import Base, engine
from app.main import app
from tests.helpers import staff_headers


def test_capacity_is_never_exceeded_under_concurrent_enrollment():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as client:
        headers = staff_headers()
        course = client.post("/courses", headers=headers, json={
            "course_code": "CONC101", "title": "Concurrency Test", "credits": 3
        }).json()
        offering = client.post("/offerings", headers=headers, json={
            "course_id": course["id"], "term_code": "TEST-TERM",
            "section_code": "A", "capacity": 5, "status": "OPEN"
        }).json()

        students = []
        for i in range(20):
            response = client.post("/students", headers=headers, json={
                "student_number": f"CONC{i:03}",
                "full_name": f"Concurrent Student {i}",
                "email": f"conc{i}@example.test",
            })
            assert response.status_code == 201
            students.append(response.json()["id"])

        def request_enrollment(item):
            index, student_id = item
            return client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
                "student_id": student_id,
                "idempotency_key": f"concurrency-key-{index:03}",
            })

        with ThreadPoolExecutor(max_workers=20) as pool:
            responses = list(pool.map(request_enrollment, enumerate(students)))

        statuses = [response.status_code for response in responses]
        assert statuses.count(201) == 5
        assert statuses.count(409) == 15

        final_offering = client.get("/offerings", params={"term": "TEST-TERM"}).json()[0]
        enrolled_rows = sum(
            len(client.get(f"/students/{student_id}/enrollments", headers=headers).json())
            for student_id in students
        )
        assert final_offering["enrolled_count"] == 5
        assert enrolled_rows == 5


def test_concurrent_duplicate_requests_leave_one_active_enrollment():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        headers = staff_headers()
        student = client.post("/students", headers=headers, json={
            "student_number": "DUP001", "full_name": "Duplicate Student",
            "email": "duplicate@example.test",
        }).json()
        course = client.post("/courses", headers=headers, json={
            "course_code": "DUP101", "title": "Duplicate Race", "credits": 3,
        }).json()
        offering = client.post("/offerings", headers=headers, json={
            "course_id": course["id"], "term_code": "DUP-TERM",
            "section_code": "A", "capacity": 5, "status": "OPEN",
        }).json()

        def enroll(key):
            return client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
                "student_id": student["id"], "idempotency_key": key,
            })

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(enroll, ["duplicate-key-001", "duplicate-key-002"]))
        assert sorted(response.status_code for response in responses) == [201, 409]
        current = client.get("/offerings", params={"term": "DUP-TERM"}, headers=headers).json()[0]
        active = client.get(f"/students/{student['id']}/enrollments", headers=headers).json()
        assert current["enrolled_count"] == 1
        assert len(active) == 1
