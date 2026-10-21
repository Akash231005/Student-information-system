"""Bounded, robots-respecting HTTPS crawler with a durable frontier.

Safety limits: public HTTPS only, no credentials or IP literals, same host as the seed,
bounded page count, depth, wall-clock time and response bytes.

What makes it a crawler rather than a fetch loop:

* robots.txt is fetched once per run and honoured (RFC 9309 semantics: 4xx means no
  restriction, 401/403 and unreachable-or-5xx mean do-not-crawl).
* Requests are spaced by the site's ``Crawl-delay`` when it publishes one, otherwise by a
  fixed polite interval. Same-host crawling is deliberately serial: parallel requests to
  one origin are what the delay exists to prevent.
* 429 and 503 are respected, including ``Retry-After``, with bounded retries.
* The frontier, the fetched pages and the run summary are persisted (see ``app.crawlstore``),
  so a crawl resumes after a restart and never refetches a URL it already holds.
"""
from __future__ import annotations

import gzip
import ipaddress
import socket
import time
from collections import deque
from html.parser import HTMLParser
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from app.crawlstore import CrawlStore

MAX_BYTES = 1_000_000
MAX_ROBOTS_BYTES = 64_000
MAX_DEPTH = 2
MAX_DELAY_SECONDS = 10.0
DEFAULT_DELAY_SECONDS = 0.5
MAX_RETRIES = 2
RETRY_STATUS = {429, 503}
USER_AGENT = (
    "SIS-Lab-Crawler/0.2 (+https://github.com/sujith0613/sis-system-design; coursework crawler)"
)


def _is_public_https(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    if parsed.port not in (None, 443):
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False
    try:
        literal = ipaddress.ip_address(host)
        if not literal.is_global:
            return False
        addresses = [literal]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(info[4][0]) for info in
                         socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]
        except (OSError, ValueError):
            return False
        if not addresses or any(not address.is_global for address in addresses):
            return False
    return True


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _is_public_https(newurl):
            return None
        old_host = urlparse(req.full_url).hostname
        if urlparse(newurl).hostname != old_host:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data.strip())


def fetch_robots(seed_url: str, timeout: float = 3.0) -> tuple[RobotFileParser, dict]:
    """Load and parse robots.txt, applying RFC 9309 reachability rules."""
    base = urlparse(seed_url)
    robots_url = f"{base.scheme}://{base.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    status = {"url": robots_url, "outcome": "unknown", "crawl_delay": None}
    request = Request(robots_url, headers={"User-Agent": USER_AGENT, "Accept": "text/plain"})
    try:
        with build_opener(_SafeRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(MAX_ROBOTS_BYTES)
        parser.parse(raw.decode("utf-8", errors="replace").splitlines())
        status["outcome"] = "parsed"
    except HTTPError as exc:
        if exc.code in (401, 403):
            parser.disallow_all = True
            status["outcome"] = f"disallowed_all_http_{exc.code}"
        elif 400 <= exc.code < 500:
            parser.allow_all = True
            status["outcome"] = f"allow_all_http_{exc.code}"
        else:
            parser.disallow_all = True
            status["outcome"] = f"disallowed_all_http_{exc.code}"
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        # RFC 9309: an unreachable robots.txt means the crawler must not proceed.
        parser.disallow_all = True
        status["outcome"] = f"disallowed_all_unreachable: {str(exc)[:120]}"
    delay = parser.crawl_delay(USER_AGENT)
    if delay is not None:
        status["crawl_delay"] = min(float(delay), MAX_DELAY_SECONDS)
    return parser, status


class _Pacer:
    """Keeps a minimum interval between requests to the same origin."""

    def __init__(self, interval: float):
        self.interval = max(0.0, interval)
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None and self.interval > 0:
            remaining = self.interval - (perf_counter() - self._last)
            if remaining > 0:
                time.sleep(remaining)
        self._last = perf_counter()


def _decode(response, raw: bytes) -> str:
    if response.headers.get("Content-Encoding", "").lower() == "gzip":
        raw = gzip.decompress(raw[:MAX_BYTES])
    charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def crawl(
    seed_url: str,
    max_pages: int = 10,
    timeout: float = 3.0,
    store: CrawlStore | None = None,
    delay: float | None = None,
) -> dict:
    """Crawl the seed's host, honouring robots.txt and its crawl delay."""
    if not _is_public_https(seed_url):
        raise ValueError("Seed must be a public, credential-free HTTPS URL")
    seed_url = urldefrag(seed_url)[0]
    seed_host = urlparse(seed_url).hostname
    started = perf_counter()

    robots, robots_status = fetch_robots(seed_url, timeout=timeout)
    if not robots.can_fetch(USER_AGENT, seed_url):
        raise ValueError(
            f"robots.txt at {robots_status['url']} does not allow this crawler "
            f"({robots_status['outcome']})"
        )
    interval = delay if delay is not None else (
        robots_status["crawl_delay"] or DEFAULT_DELAY_SECONDS
    )
    pacer = _Pacer(interval)

    resumed_from = 0
    if store is not None:
        store.enqueue([(seed_url, 0)], seed_url)
        pending = store.pending(seed_url, max_pages)
        resumed_from = len(pending)
        queue = deque((row["url"], row["depth"]) for row in pending)
    else:
        queue = deque([(seed_url, 0)])

    queued = {url for url, _ in queue}
    pages: list[dict] = []
    errors: list[dict] = []
    retries = 0
    attempts = 0
    # Bound the work even when most of the frontier fails, so one request cannot crawl an
    # unbounded queue of dead links.
    max_attempts = max_pages * 3
    opener = build_opener(_SafeRedirect())

    while queue and len(pages) < max_pages and attempts < max_attempts:
        url, depth = queue.popleft()
        attempts += 1
        if store is not None:
            store.claim(url)

        request = Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "identity",
        })
        html = None
        final_url = url
        for attempt in range(MAX_RETRIES + 1):
            pacer.wait()
            try:
                with opener.open(request, timeout=timeout) as response:
                    final_url = response.geturl()
                    if not _is_public_https(final_url) or urlparse(final_url).hostname != seed_host:
                        errors.append({"url": url,
                                       "error": "redirect escaped the seed host or public HTTPS policy"})
                        html = None
                        break
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "text/html" not in content_type:
                        html = None
                        break
                    raw = response.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        errors.append({"url": url, "error": "page exceeded 1 MB limit"})
                        html = None
                        break
                    html = _decode(response, raw)
                break
            except HTTPError as exc:
                if exc.code in RETRY_STATUS and attempt < MAX_RETRIES:
                    retries += 1
                    wait = _retry_after(exc) or (2 ** attempt)
                    time.sleep(min(wait, MAX_DELAY_SECONDS))
                    continue
                if exc.code in {301, 302, 303, 307, 308}:
                    # urllib raises the raw 302 when our handler refuses to follow it, which
                    # is the same-host / public-HTTPS policy doing its job.
                    errors.append({"url": url,
                                   "error": f"HTTP {exc.code} redirect refused (leaves the seed host)"})
                    break
                errors.append({"url": url, "error": f"HTTP {exc.code}"[:180]})
                break
            except (URLError, TimeoutError, OSError, ValueError) as exc:
                if attempt < MAX_RETRIES:
                    retries += 1
                    time.sleep(min(2 ** attempt, MAX_DELAY_SECONDS))
                    continue
                errors.append({"url": url, "error": str(exc)[:180]})
                break

        if html is None:
            if store is not None:
                failure = next((e for e in reversed(errors) if e["url"] == url), None)
                if failure:
                    store.record_error(seed_url, url, failure["error"])
            continue

        parser = _LinkParser()
        parser.feed(html)
        page = {
            "url": final_url,
            # The frontier is keyed by the URL we asked for, not where it redirected to;
            # otherwise a redirect makes the same URL look unseen on the next run.
            "requested_url": url,
            "title": " ".join(parser.title_parts).strip()[:200],
            "depth": depth,
            "links_found": len(parser.links),
        }
        pages.append(page)
        if store is not None:
            store.record_page(seed_url, page)

        if depth + 1 > MAX_DEPTH:
            continue
        discovered: list[tuple[str, int]] = []
        for href in parser.links:
            candidate = urldefrag(urljoin(final_url, href))[0]
            if candidate in queued or urlparse(candidate).hostname != seed_host:
                continue
            if store is not None and store.seen(candidate):
                continue  # already fetched by an earlier run; the store is the dedupe authority
            if not _is_public_https(candidate) or not robots.can_fetch(USER_AGENT, candidate):
                continue
            queued.add(candidate)
            discovered.append((candidate, depth + 1))
            queue.append((candidate, depth + 1))
        if store is not None and discovered:
            store.enqueue(discovered, seed_url)

    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    elapsed_seconds = max(elapsed_ms / 1000, 0.001)
    result = {
        "seed": seed_url,
        "pages_crawled": len(pages),
        "pages": pages,
        "errors": errors,
        "frontier_remaining": len(queue),
        "elapsed_ms": elapsed_ms,
        "pages_per_second": round(len(pages) / elapsed_seconds, 2),
        "robots": robots_status,
        "politeness_seconds": interval,
        "retries": retries,
        "attempts": attempts,
        "resumed_from_frontier": resumed_from,
        "limits": {"max_pages": max_pages, "max_depth": MAX_DEPTH,
                   "max_attempts": max_attempts, "max_response_bytes": MAX_BYTES},
    }
    if store is not None:
        result["stored_run_id"] = store.record_run({
            "seed": seed_url,
            "pages_crawled": len(pages),
            "errors": len(errors),
            "elapsed_ms": elapsed_ms,
            "politeness_seconds": interval,
            "robots_outcome": robots_status["outcome"],
        })
        result["frontier_pending_total"] = store.pending_count()
    return result


def _retry_after(exc: HTTPError) -> float | None:
    value = exc.headers.get("Retry-After") if exc.headers else None
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
