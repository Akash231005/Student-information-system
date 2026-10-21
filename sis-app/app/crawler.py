"""Bounded same-host HTTPS crawler used for the system-design lab demo.

Safety limits: public HTTPS only, no credentials/IP literals, same host as seed, bounded pages,
timeouts and response bytes. It is still a coursework example, not a hardened general crawler.
"""
import ipaddress
import socket
from collections import deque
from html.parser import HTMLParser
from time import perf_counter
from urllib.error import URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 1_000_000
USER_AGENT = "SIS-Lab-Crawler/0.1 (coursework demo)"


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


def crawl(seed_url: str, max_pages: int = 10, timeout: float = 3.0) -> dict:
    if not _is_public_https(seed_url):
        raise ValueError("Seed must be a public, credential-free HTTPS URL")
    seed_url = urldefrag(seed_url)[0]
    started = perf_counter()
    seed_host = urlparse(seed_url).hostname
    queue = deque([(seed_url, 0)])
    queued = {seed_url}
    visited: set[str] = set()
    pages = []
    errors = []
    opener = build_opener(_SafeRedirect())
    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        try:
            with opener.open(request, timeout=timeout) as response:
                final_url = response.geturl()
                if not _is_public_https(final_url) or urlparse(final_url).hostname != seed_host:
                    errors.append({"url": url, "error": "redirect escaped the seed host or public HTTPS policy"})
                    continue
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" not in content_type:
                    continue
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    errors.append({"url": url, "error": "page exceeded 1 MB limit"})
                    continue
                html = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append({"url": url, "error": str(exc)[:180]})
            continue
        parser = _LinkParser()
        parser.feed(html)
        pages.append({"url": final_url, "title": " ".join(parser.title_parts).strip(),
                      "depth": depth, "links_found": len(parser.links)})
        if depth + 1 >= 3:
            continue
        for href in parser.links:
            candidate = urldefrag(urljoin(final_url, href))[0]
            parsed = urlparse(candidate)
            if parsed.hostname == seed_host and candidate not in queued and _is_public_https(candidate):
                queued.add(candidate)
                queue.append((candidate, depth + 1))
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    elapsed_seconds = max(elapsed_ms / 1000, 0.001)
    return {"seed": seed_url, "pages_crawled": len(pages), "pages": pages,
            "errors": errors, "frontier_remaining": len(queue),
            "elapsed_ms": elapsed_ms,
            "pages_per_second": round(len(pages) / elapsed_seconds, 2),
            "limits": {"max_pages": max_pages, "max_depth": 2, "max_response_bytes": MAX_BYTES}}
