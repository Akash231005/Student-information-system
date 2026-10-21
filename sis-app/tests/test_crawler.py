"""Crawler tests: robots.txt policy and frontier building via a scripted opener, plus one
real crawl of a live site so the fetch path is exercised against the network too.
"""
import os
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient

from app.crawler import _is_public_https, crawl
from app.main import app

ROBOTS_ALLOW_ALL = b"User-agent: *\nDisallow:\n"


class _FakeHeaders(dict):
    def get_content_charset(self):
        return "utf-8"


class _FakeResponse:
    def __init__(self, body: bytes, url: str, content_type: str = "text/html; charset=utf-8"):
        self._body = body
        self._url = url
        self.headers = _FakeHeaders({"Content-Type": content_type})

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self):
        return self._url

    def read(self, _limit):
        return self._body


class _ScriptedOpener:
    """Serves robots.txt and pages from a dict so the test never touches the network."""

    def __init__(self, pages: dict[str, bytes], unreachable: set[str] | None = None):
        self.pages = pages
        self.unreachable = unreachable or set()
        self.requested: list[str] = []

    def open(self, request, timeout):
        url = request.full_url
        self.requested.append(url)
        if url in self.unreachable:
            raise URLError("connection refused")
        body = self.pages.get(url)
        if body is None:
            raise HTTPError(url, 404, "not found", None, None)
        return _FakeResponse(body, url)


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


def _install(monkeypatch, pages, unreachable=None):
    opener = _ScriptedOpener(pages, unreachable)
    monkeypatch.setattr("app.crawler._is_public_https", lambda _url: True)
    monkeypatch.setattr("app.crawler.build_opener", lambda *_args: opener)
    return opener


def test_robots_disallow_prevents_the_crawl(monkeypatch):
    _install(monkeypatch, {
        "https://example.test/robots.txt": b"User-agent: *\nDisallow: /private\n",
        "https://example.test/private/page": b"<html><title>secret</title></html>",
    })
    with pytest.raises(ValueError, match="robots.txt"):
        crawl("https://example.test/private/page", max_pages=1)


def test_robots_crawl_delay_sets_the_request_interval(monkeypatch):
    _install(monkeypatch, {
        "https://example.test/robots.txt": b"User-agent: *\nCrawl-delay: 2\nDisallow:\n",
        "https://example.test/": b"<html><title>Home</title></html>",
    })
    result = crawl("https://example.test/", max_pages=1)
    assert result["politeness_seconds"] == 2.0
    assert result["robots"]["outcome"] == "parsed"
    assert result["robots"]["crawl_delay"] == 2.0


def test_crawler_parses_page_and_keeps_the_frontier_on_one_host(monkeypatch):
    opener = _install(monkeypatch, {
        "https://example.test/robots.txt": ROBOTS_ALLOW_ALL,
        "https://example.test/": (
            b"<html><title>Example Test</title>"
            b"<a href='/next'>next</a>"
            b"<a href='https://other.test/'>external</a></html>"
        ),
    })
    result = crawl("https://example.test/", max_pages=1, delay=0)
    assert result["pages_crawled"] == 1
    assert result["pages"][0]["title"] == "Example Test"
    assert result["pages"][0]["links_found"] == 2
    assert result["frontier_remaining"] == 1
    assert result["pages_per_second"] > 0
    assert result["limits"]["max_depth"] == 2
    assert not any("other.test" in url for url in opener.requested)


def test_unreachable_robots_txt_blocks_the_crawl(monkeypatch):
    # RFC 9309: no robots.txt reachable means do not crawl, not "assume anything goes".
    _install(
        monkeypatch,
        {"https://example.test/": b"<html><title>Home</title></html>"},
        unreachable={"https://example.test/robots.txt"},
    )
    with pytest.raises(ValueError, match="robots.txt"):
        crawl("https://example.test/", max_pages=1)


def test_missing_robots_txt_allows_the_crawl(monkeypatch):
    # A 404 means "no restrictions published", which is different from unreachable.
    _install(monkeypatch, {"https://example.test/": b"<html><title>Home</title></html>"})
    result = crawl("https://example.test/", max_pages=1, delay=0)
    assert result["robots"]["outcome"] == "allow_all_http_404"
    assert result["pages_crawled"] == 1


@pytest.mark.skipif(
    os.environ.get("SIS_LIVE_CRAWL") != "1",
    reason="opt in with SIS_LIVE_CRAWL=1; the suite must not hit a third-party site by default",
)
def test_live_crawl_fetches_a_real_page():
    result = crawl("https://www.iana.org/", max_pages=1, delay=0)
    assert result["pages_crawled"] >= 1
    assert result["pages"][0]["url"].startswith("https://www.iana.org/")
    assert result["robots"]["outcome"].startswith(("parsed", "allow_all"))
