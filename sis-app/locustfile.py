"""Default course-discovery workload. Use the dedicated locust_*.py files for other workloads."""
from locust import HttpUser, between, task


class CourseSearchUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(5)
    def list_courses(self):
        self.client.get("/courses", name="GET /courses")

    @task(3)
    def search_by_title(self):
        self.client.get("/courses", params={"q": "system"}, name="GET /courses?q=system")

    @task(2)
    def list_offerings(self):
        self.client.get("/offerings", params={"term": "2026-FALL"}, name="GET /offerings")
