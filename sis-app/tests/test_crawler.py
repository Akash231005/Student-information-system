from fastapi.testclient import TestClient

from app.crawler import _is_public_https, crawl
from app.main import app


def test_crawler_rejects_private_hosts_and_non_https():
    assert not _is_public_https("http://example.com")
    assert not _is_public_https("https://127.0.0.1/")
    assert not _is_public_https("https://localhost/")
    assert not _is_public_https("https://user:pass@example.com/")
    assert not _is_public_https("https://example.com:8443/")


def test_crawler_endpoint_rejects_unsafe_seed():
    with TestClient(app) as client:
        response = client.post("/system-design/crawler/run", json={
            "seed_url": "http://127.0.0.1:8000/", "max_pages": 2,
        })
        assert response.status_code == 422


def test_crawler_parses_page_and_builds_same_host_frontier(monkeypatch):
    class FakeHeaders(dict):
        def get_content_charset(self):
            return "utf-8"

    class FakeResponse:
        headers = FakeHeaders({"Content-Type": "text/html; charset=utf-8"})

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def geturl(self):
            return "https://example.test/"

        def read(self, _limit):
            return (b"<html><title>Example Test</title>"
                    b"<a href='/next'>next</a>"
                    b"<a href='https://other.test/'>external</a></html>")

    class FakeOpener:
        def open(self, _request, timeout):
            assert timeout == 3.0
            return FakeResponse()

    monkeypatch.setattr("app.crawler._is_public_https", lambda _url: True)
    monkeypatch.setattr("app.crawler.build_opener", lambda *_args: FakeOpener())

    result = crawl("https://example.test/", max_pages=1)
    assert result["pages_crawled"] == 1
    assert result["pages"][0]["title"] == "Example Test"
    assert result["pages"][0]["links_found"] == 2
    assert result["frontier_remaining"] == 1
    assert result["elapsed_ms"] >= 0
    assert result["pages_per_second"] > 0
    assert result["limits"]["max_depth"] == 2
