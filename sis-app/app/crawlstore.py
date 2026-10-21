"""Durable crawl state in MongoDB.

Three collections make a crawl resumable and idempotent instead of a fire-and-forget loop:

    crawl_frontier  URLs discovered but not yet fetched (the queue survives a restart)
    crawl_pages     every page actually fetched, keyed by URL (this is the cross-run dedupe)
    crawl_runs      one document per crawl run, with its measured outcome

Deduplication is therefore a property of the store, not of a Python set: a second run over
the same seed re-fetches nothing it has already seen.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING
from pymongo.database import Database

FRONTIER = "crawl_frontier"
PAGES = "crawl_pages"
RUNS = "crawl_runs"


def _now() -> datetime:
    return datetime.now(UTC)


class CrawlStore:
    def __init__(self, db: Database):
        self.frontier = db[FRONTIER]
        self.pages = db[PAGES]
        self.runs = db[RUNS]

    def init(self) -> None:
        """Create the frontier index. Called at startup, so constructing the store is free."""
        self.frontier.create_index([("seed", ASCENDING), ("depth", ASCENDING)])

    # ------------------------------------------------------------------- frontier

    def enqueue(self, urls: list[tuple[str, int]], seed: str) -> int:
        """Queue URLs, skipping anything already fetched in a previous run."""
        added = 0
        for url, depth in urls:
            if self.seen(url):
                continue
            result = self.frontier.update_one(
                {"_id": url},
                {"$setOnInsert": {"url": url, "seed": seed, "depth": depth, "queued_at": _now()}},
                upsert=True,
            )
            added += result.upserted_id is not None
        return added

    def pending(self, seed: str, limit: int) -> list[dict[str, Any]]:
        return list(self.frontier.find({"seed": seed}).sort("depth", ASCENDING).limit(limit))

    def claim(self, url: str) -> None:
        """Remove from the frontier before fetching so a crash cannot loop on one URL."""
        self.frontier.delete_one({"_id": url})

    def pending_count(self, seed: str | None = None) -> int:
        return self.frontier.count_documents({} if seed is None else {"seed": seed})

    # ---------------------------------------------------------------- observations

    def seen(self, url: str) -> bool:
        return self.pages.count_documents({"_id": url}, limit=1) == 1

    def record_page(self, seed: str, page: dict[str, Any]) -> None:
        key = page.get("requested_url") or page["url"]
        self.pages.replace_one(
            {"_id": key},
            {**page, "seed": seed, "fetched_at": _now()},
            upsert=True,
        )

    def record_error(self, seed: str, url: str, error: str) -> None:
        self.pages.replace_one(
            {"_id": url},
            {"url": url, "seed": seed, "error": error, "fetched_at": _now()},
            upsert=True,
        )

    def record_run(self, summary: dict[str, Any]) -> str:
        summary = {**summary, "finished_at": _now()}
        return str(self.runs.insert_one(summary).inserted_id)

    # ------------------------------------------------------------------- reporting

    def stats(self) -> dict[str, Any]:
        pages = self.pages.count_documents({"error": {"$exists": False}})
        errors = self.pages.count_documents({"error": {"$exists": True}})
        last_run = self.runs.find_one(sort=[("finished_at", -1)])
        if last_run:
            last_run.pop("_id", None)
        return {
            "pages_stored": pages,
            "errors_stored": errors,
            "frontier_pending": self.pending_count(),
            "runs_recorded": self.runs.count_documents({}),
            "last_run": _jsonable(last_run),
        }

    def recent_pages(self, limit: int = 25) -> list[dict[str, Any]]:
        cursor = self.pages.find({"error": {"$exists": False}}).sort("fetched_at", -1).limit(limit)
        return [_jsonable({k: v for k, v in doc.items() if k != "_id"}) for doc in cursor]

    def reset(self, seed: str | None = None) -> dict[str, int]:
        query = {} if seed is None else {"seed": seed}
        return {
            "pages_deleted": self.pages.delete_many(query).deleted_count,
            "frontier_deleted": self.frontier.delete_many(query).deleted_count,
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
