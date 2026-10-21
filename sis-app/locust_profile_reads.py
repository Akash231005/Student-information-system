import os
import uuid

from locust import HttpUser, between, task


class ProfileReadLoad(HttpUser):
    wait_time = between(0.1, 0.4)

    def on_start(self):
        self.student_id = os.getenv("SIS_STUDENT_ID")
        token = os.getenv("SIS_TOKEN")
        if not token or not self.student_id:
            suffix = uuid.uuid4().hex[:16]
            password = "load-test-password-long"
            created = self.client.post("/auth/register", json={
                "student_number": f"PROFILE-{suffix}",
                "full_name": "Profile Load Student",
                "email": f"profile-{suffix}@example.test",
                "password": password,
            }, name="SETUP /auth/register")
            if created.status_code != 201:
                self.stop(True)
                return
            self.student_id = created.json()["student_id"]
            login = self.client.post("/auth/login", json={
                "email": f"profile-{suffix}@example.test", "password": password,
            }, name="SETUP /auth/login")
            if login.status_code != 200:
                self.stop(True)
                return
            token = login.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(4)
    def profile(self):
        self.client.get(f"/students/{self.student_id}", name="GET /students/{id}")

    @task(3)
    def enrollments(self):
        self.client.get(f"/students/{self.student_id}/enrollments",
                        name="GET /students/{id}/enrollments")

    @task(2)
    def grades(self):
        self.client.get(f"/students/{self.student_id}/grades",
                        name="GET /students/{id}/grades")

    @task(1)
    def timetable(self):
        self.client.get("/timetable", params={"term": "SYNTHETIC-2026"},
                        name="GET /timetable")
