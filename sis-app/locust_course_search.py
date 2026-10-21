from locust import HttpUser, between, task


class CourseSearchLoad(HttpUser):
    wait_time = between(0.1, 0.4)

    @task(5)
    def list_courses(self):
        self.client.get("/courses", name="GET /courses")

    @task(3)
    def search_courses(self):
        self.client.get("/courses", params={"q": "synthetic"}, name="GET /courses?q=synthetic")

    @task(2)
    def list_offerings(self):
        self.client.get("/offerings", params={"term": "SYNTHETIC-2026"}, name="GET /offerings")
