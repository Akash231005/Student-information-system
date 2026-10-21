import uuid

from locust import HttpUser, between, task


class StudentWriteLoad(HttpUser):
    wait_time = between(0.2, 0.6)

    @task
    def register_student(self):
        token = uuid.uuid4().hex
        self.client.post("/auth/register", json={
            "student_number": f"LOAD-{token[:20]}",
            "full_name": "Synthetic Load Student",
            "email": f"load-{token}@example.test",
            "password": "load-test-password-long",
        }, name="POST /auth/register")
