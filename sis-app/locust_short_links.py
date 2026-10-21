"""Measure short-link creation and redirect latency.

Set SIS_STAFF_TOKEN to a bearer token for a local staff account. Redirects are not followed,
so Locust measures the SIS redirect endpoint rather than the external destination.
"""
import os

from locust import HttpUser, between, task


class ShortLinkUser(HttpUser):
    wait_time = between(0.2, 0.6)

    def on_start(self):
        token = os.getenv("SIS_STAFF_TOKEN")
        if not token:
            self.stop(True)
            return
        self.client.headers.update({"Authorization": f"Bearer {token}"})
        response = self.client.post(
            "/short-links",
            json={"url": "https://example.com/course-info"},
            name="SETUP POST /short-links",
        )
        if response.status_code != 201:
            self.stop(True)
            return
        self.short_path = response.json()["path"]

    @task
    def redirect(self):
        path = getattr(self, "short_path", None)
        if path:
            self.client.get(path, allow_redirects=False, name="GET /s/{code}")
