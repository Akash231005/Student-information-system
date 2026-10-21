from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from tests.helpers import staff_headers


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_attendance_grade_timetable_and_notifications():
    with TestClient(app) as client:
        headers = staff_headers()
        student = client.post("/students", headers=headers, json={
            "student_number": "ACA001", "full_name": "Academic Student",
            "email": "academic@example.test",
        }).json()
        course = client.post("/courses", headers=headers, json={
            "course_code": "ACA101", "title": "Academic Features", "credits": 3,
        }).json()
        offering = client.post("/offerings", headers=headers, json={
            "course_id": course["id"], "term_code": "2026-FALL",
            "section_code": "A", "capacity": 2, "status": "OPEN",
        }).json()

        enrolled = client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
            "student_id": student["id"], "idempotency_key": "academic-key-001",
        })
        assert enrolled.status_code == 201

        attendance = client.post("/attendance", headers=headers, json={
            "student_id": student["id"], "offering_id": offering["id"],
            "session_date": "2026-10-19", "status": "PRESENT",
        })
        assert attendance.status_code == 201
        assert client.post("/attendance", headers=headers, json={
            "student_id": student["id"], "offering_id": offering["id"],
            "session_date": "2026-10-19", "status": "PRESENT",
        }).status_code == 409

        assessment = client.post("/assessments", headers=headers, json={
            "offering_id": offering["id"], "title": "Midterm", "max_marks": 50,
            "assessment_date": "2026-10-20",
        })
        assert assessment.status_code == 201
        grade = client.post(f"/assessments/{assessment.json()['id']}/grades", headers=headers, json={
            "student_id": student["id"], "marks": 42,
        })
        assert grade.status_code == 201
        assert client.post(f"/assessments/{assessment.json()['id']}/grades", headers=headers, json={
            "student_id": student["id"], "marks": 51,
        }).status_code == 422

        timetable = client.post("/timetable", headers=headers, json={
            "offering_id": offering["id"], "day_of_week": 0,
            "start_time": "09:00", "end_time": "10:00", "room": "LH-15",
            "term_code": "2026-FALL",
        })
        assert timetable.status_code == 201
        assert len(client.get("/timetable", params={"term": "2026-FALL"}).json()) == 1

        notification = client.post("/notifications", headers=headers, json={
            "student_id": student["id"], "title": "Exam reminder",
            "message": "Midterm tomorrow",
        })
        assert notification.status_code == 201
        assert len(client.get(f"/students/{student['id']}/notifications", headers=headers).json()) == 1


def test_shard_store_and_ring_endpoints():
    with TestClient(app) as client:
        put = client.put("/system-design/sharded-records/student-42", json={"credits": 20})
        assert put.status_code == 200
        get = client.get("/system-design/sharded-records/student-42")
        assert get.status_code == 200
        assert get.json()["value"]["credits"] == 20
        assert client.get("/system-design/sharded-records").json()["total_records"] >= 1

def test_drop_releases_seat_exactly_once():
    with TestClient(app) as client:
        headers = staff_headers()
        student = client.post("/students", headers=headers, json={
            "student_number": "DROP001", "full_name": "Drop Student",
            "email": "drop@example.test",
        }).json()
        course = client.post("/courses", headers=headers, json={
            "course_code": "DROP101", "title": "Drop Test", "credits": 3,
        }).json()
        offering = client.post("/offerings", headers=headers, json={
            "course_id": course["id"], "term_code": "DROP-TERM",
            "section_code": "A", "capacity": 1, "status": "OPEN",
        }).json()
        enrolled = client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
            "student_id": student["id"], "idempotency_key": "drop-key-001",
        }).json()
        dropped = client.post(f"/enrollments/{enrolled['id']}/drop", headers=headers)
        assert dropped.status_code == 200
        assert dropped.json()["remaining_seats"] == 1
        assert client.post(f"/enrollments/{enrolled['id']}/drop", headers=headers).status_code == 409
        rejoined = client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
            "student_id": student["id"], "idempotency_key": "drop-key-002",
        })
        assert rejoined.status_code == 201
        current = client.get("/offerings", params={"term": "DROP-TERM"}, headers=headers).json()[0]
        assert current["enrolled_count"] == 1

from concurrent.futures import ThreadPoolExecutor


def test_concurrent_drop_and_enroll_keeps_counter_consistent():
    with TestClient(app) as client:
        headers = staff_headers()
        students = []
        for i in range(2):
            students.append(client.post("/students", headers=headers, json={
                "student_number": f"RACE{i:03}",
                "full_name": f"Race Student {i}",
                "email": f"race{i}@example.test",
            }).json())
        course = client.post("/courses", headers=headers, json={
            "course_code": "RACE101", "title": "Drop/Enroll Race", "credits": 3,
        }).json()
        offering = client.post("/offerings", headers=headers, json={
            "course_id": course["id"], "term_code": "RACE-TERM",
            "section_code": "A", "capacity": 2, "status": "OPEN",
        }).json()
        enrolled = client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
            "student_id": students[0]["id"], "idempotency_key": "race-key-0001",
        }).json()

        def drop():
            return client.post(f"/enrollments/{enrolled['id']}/drop", headers=headers)

        def enroll_other():
            return client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
                "student_id": students[1]["id"], "idempotency_key": "race-key-0002",
            })

        with ThreadPoolExecutor(max_workers=2) as pool:
            dropped, added = list(pool.map(lambda fn: fn(), [drop, enroll_other]))
        assert dropped.status_code == 200
        assert added.status_code in {201, 409}
        if added.status_code == 409:
            # A request that races ahead of the seat release may legitimately fail fast;
            # retrying after the drop transaction commits should observe the free seat.
            added = client.post(f"/offerings/{offering['id']}/enroll", headers=headers, json={
                "student_id": students[1]["id"], "idempotency_key": "race-key-retry",
            })
            assert added.status_code == 201
        final_offering = client.get("/offerings", params={"term": "RACE-TERM"}, headers=headers).json()[0]
        assert final_offering["enrolled_count"] == 1
        active = sum(len(client.get(f"/students/{s['id']}/enrollments", headers=headers).json()) for s in students)
        assert active == 1
