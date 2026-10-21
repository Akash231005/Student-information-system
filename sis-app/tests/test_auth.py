from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from tests.helpers import staff_headers


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_register_login_and_record_level_authorization():
    with TestClient(app) as client:
        registered = client.post("/auth/register", json={
            "student_number": "AUTH001",
            "full_name": "Auth Student",
            "email": "auth@example.test",
            "password": "correct-horse-battery",
        })
        assert registered.status_code == 201

        login = client.post("/auth/login", json={
            "email": "auth@example.test",
            "password": "correct-horse-battery",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "auth@example.test"
        own_profile = client.get(f"/students/{registered.json()['student_id']}", headers=headers)
        assert own_profile.status_code == 200
        updated = client.patch(f"/students/{registered.json()['student_id']}", headers=headers,
                               json={"full_name": "Updated Auth Student"})
        assert updated.status_code == 200
        assert updated.json()["full_name"] == "Updated Auth Student"

        other = client.post("/auth/register", json={
            "student_number": "AUTH002", "full_name": "Other Student",
            "email": "other-auth@example.test", "password": "another-correct-password",
        })
        forbidden = client.get(f"/students/{other.json()['student_id']}", headers=headers)
        assert forbidden.status_code == 403
        forbidden_update = client.patch(f"/students/{other.json()['student_id']}", headers=headers,
                                        json={"full_name": "Hijack Attempt"})
        assert forbidden_update.status_code == 403

        denied = client.post("/auth/login", json={
            "email": "auth@example.test", "password": "wrong-password"
        })
        assert denied.status_code == 401


def test_student_cannot_create_staff_resources():
    with TestClient(app) as client:
        client.post("/auth/register", json={
            "student_number": "AUTH003", "full_name": "Student",
            "email": "student-auth@example.test", "password": "student-password-long",
        }).json()
        login = client.post("/auth/login", json={
            "email": "student-auth@example.test", "password": "student-password-long",
        }).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        denied = client.post("/courses", headers=headers, json={
            "course_code": "NOPE101", "title": "Forbidden Course", "credits": 3,
        })
        assert denied.status_code == 403


def test_autocomplete_and_short_link():
    with TestClient(app) as client:
        headers = staff_headers()
        course = client.post("/courses", headers=headers, json={
            "course_code": "SYS200", "title": "Scalable Systems", "credits": 3
        })
        assert course.status_code == 201
        response = client.get("/autocomplete", params={"q": "SYS"})
        assert response.status_code == 200
        assert response.json()["items"][0]["course_code"] == "SYS200"
        assert response.json()["cache"] == "MISS"
        warm = client.get("/autocomplete", params={"q": "SYS"})
        assert warm.json()["cache"] == "HIT"

        short = client.post("/short-links", headers=headers,
                            json={"url": "https://example.com/course/123"})
        assert short.status_code == 201
        assert client.get(short.json()["path"], follow_redirects=False).status_code == 307


def test_notifications_are_private_to_their_owner():
    with TestClient(app) as client:
        client.post("/auth/register", json={
            "student_number": "NOTICE001", "full_name": "Notification Owner",
            "email": "notice-owner@example.test", "password": "owner-password-long",
        }).json()
        other = client.post("/auth/register", json={
            "student_number": "NOTICE002", "full_name": "Other Student",
            "email": "notice-other@example.test", "password": "other-password-long",
        }).json()
        staff = staff_headers()
        notification = client.post("/notifications", headers=staff, json={
            "student_id": other["student_id"], "title": "Exam notice", "message": "Exam tomorrow",
        })
        assert notification.status_code == 201

        owner_token = client.post("/auth/login", json={
            "email": "notice-owner@example.test", "password": "owner-password-long",
        }).json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        assert client.get(f"/students/{other['student_id']}/notifications",
                          headers=owner_headers).status_code == 403
        assert client.post(f"/notifications/{notification.json()['id']}/read",
                           headers=owner_headers).status_code == 403

        other_token = client.post("/auth/login", json={
            "email": "notice-other@example.test", "password": "other-password-long",
        }).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        assert client.get(f"/students/{other['student_id']}/notifications",
                          headers=other_headers).status_code == 200
        assert client.post(f"/notifications/{notification.json()['id']}/read",
                           headers=other_headers).status_code == 200



def test_course_creation_invalidates_autocomplete_cache():
    with TestClient(app) as client:
        headers = staff_headers()
        first = client.post("/courses", headers=headers, json={
            "course_code": "SYS300", "title": "Systems Design", "credits": 3,
        })
        assert first.status_code == 201
        assert client.get("/autocomplete", params={"q": "SYS"}).json()["cache"] == "MISS"
        assert client.get("/autocomplete", params={"q": "SYS"}).json()["cache"] == "HIT"
        second = client.post("/courses", headers=headers, json={
            "course_code": "SYS301", "title": "Systems Architecture", "credits": 4,
        })
        assert second.status_code == 201
        refreshed = client.get("/autocomplete", params={"q": "SYS"})
        assert refreshed.status_code == 200
        assert refreshed.json()["cache"] == "MISS"
        assert len(refreshed.json()["items"]) == 2
