"""Shared clients for the external state stores.

Redis is the single source of shared mutable state: rate-limit buckets, the autocomplete
cache and the ID-generator worker counter. MongoDB (reached through the mongos router) is
the sharded record store and the durable crawl frontier.

Both are hard dependencies. The application refuses to start if either is unreachable,
because quietly falling back to per-process dictionaries would make the rate-limit and
cache guarantees false while still appearing to work.
"""
from __future__ import annotations

import atexit
from threading import Lock
from typing import Any

import redis as redis_lib
from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

_redis: redis_lib.Redis | None = None
_mongo: MongoClient | None = None
_lock = Lock()

# Fail fast instead of hanging for the default 30 s when mongos is not up.
MONGO_SELECTION_TIMEOUT_MS = 2000


def get_redis() -> redis_lib.Redis:
    global _redis
    with _lock:
        if _redis is None:
            _redis = redis_lib.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30,
            )
        return _redis


def get_mongo_client() -> MongoClient:
    global _mongo
    with _lock:
        if _mongo is None:
            _mongo = MongoClient(
                settings.mongo_uri,
                serverSelectionTimeoutMS=MONGO_SELECTION_TIMEOUT_MS,
                appname="sis-lab",
            )
        return _mongo


def get_mongo_db() -> Database:
    return get_mongo_client()[settings.mongo_db]


def dependency_report() -> dict[str, Any]:
    """Ping both stores. Returns a report; raises RuntimeError if either is down."""
    problems: list[str] = []
    report: dict[str, Any] = {}

    try:
        client = get_redis()
        info = client.info()
        report["redis"] = {
            "url": settings.redis_url,
            "version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "maxmemory_policy": info.get("maxmemory_policy"),
        }
    except Exception as exc:  # noqa: BLE001 - surfaced as a startup failure below
        problems.append(f"Redis unreachable at {settings.redis_url}: {exc}")

    try:
        client = get_mongo_client()
        hello = client.admin.command("hello")
        report["mongodb"] = {
            "uri": settings.mongo_uri,
            "version": client.server_info().get("version"),
            "is_mongos": bool(hello.get("msg") == "isdbgrid"),
            "database": settings.mongo_db,
        }
    except Exception as exc:  # noqa: BLE001 - surfaced as a startup failure below
        problems.append(f"MongoDB (mongos) unreachable at {settings.mongo_uri}: {exc}")

    if problems:
        raise RuntimeError(
            "Required state stores are not available:\n  - "
            + "\n  - ".join(problems)
            + "\nStart the stack with `bash scripts/start_stack.sh` from the repository root."
        )
    return report


def close_dependencies() -> None:
    """Close both clients. Registered with atexit, not per-request-lifespan.

    The components hold these clients for the life of the process, so closing them on an
    ASGI shutdown would leave every rate-limit and cache object pointing at a dead socket.
    """
    global _redis, _mongo
    with _lock:
        if _redis is not None:
            _redis.close()
            _redis = None
        if _mongo is not None:
            _mongo.close()
            _mongo = None


atexit.register(close_dependencies)
