from locust import HttpUser, between, task


class AutocompleteLoad(HttpUser):
    wait_time = between(0.1, 0.4)

    @task(5)
    def warm_prefix(self):
        self.client.get("/autocomplete", params={"q": "SYN"}, name="GET /autocomplete?q=SYN")

    @task(2)
    def course_code_prefix(self):
        self.client.get("/autocomplete", params={"q": "SYN00"}, name="GET /autocomplete?q=SYN00")

    @task(1)
    def title_prefix(self):
        self.client.get("/autocomplete", params={"q": "Synthetic"}, name="GET /autocomplete?q=Synthetic")
