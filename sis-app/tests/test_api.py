from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from tests.helpers import staff_headers


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_enrollment_happy_path_and_capacity():
    with TestClient(app) as client:
        headers = staff_headers()
        student = client.post("/students", headers=headers, json={
            "student_number": "S001", "full_name": "Test Student", "email": "s001@example.test"
        })
        assert student.status_code == 201
        course = client.post("/courses", headers=headers, json={
            "course_code": "CS101", "title": "System Design", "credits": 4
        })
        assert course.status_code == 201
        offering = client.post("/offerings", headers=headers, json={
            "course_id": course.json()["id"], "term_code": "2026-FALL",
            "section_code": "A", "capacity": 1, "status": "OPEN"
        })
        assert offering.status_code == 201
        offering_id = offering.json()["id"]
        student_id = student.json()["id"]

        enrolled = client.post(f"/offerings/{offering_id}/enroll", headers=headers, json={
            "student_id": student_id, "idempotency_key": "test-key-0001"
        })
        assert enrolled.status_code == 201

        duplicate_retry = client.post(f"/offerings/{offering_id}/enroll", headers=headers, json={
            "student_id": student_id, "idempotency_key": "test-key-0001"
        })
        assert duplicate_retry.status_code == 201

        other = client.post("/students", headers=headers, json={
            "student_number": "S002", "full_name": "Second Student", "email": "s002@example.test"
        })
        full = client.post(f"/offerings/{offering_id}/enroll", headers=headers, json={
            "student_id": other.json()["id"], "idempotency_key": "test-key-0002"
        })
        assert full.status_code == 409
        listed = client.get(f"/students/{student_id}/enrollments", headers=headers)
        assert len(listed.json()) == 1

def test_dashboard_and_component_metrics():
    with TestClient(app) as client:
        dashboard = client.get("/")
        assert dashboard.status_code == 200
        assert "Orbit SIS" in dashboard.text or "Student Information System" in dashboard.text
        metrics = client.get("/system-design/http-metrics")
        assert metrics.status_code == 200
        assert "latency_ms" in metrics.json()
