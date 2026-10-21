"""End-to-end verification of the real state stores.

Run with the stack up (`bash scripts/start_stack.sh`):

    cd sis-app && uv run python scripts/verify_stack.py

Every number printed here is measured against the running services, so the output can be
quoted as evidence instead of describing what the code intends to do.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.components import RedisTokenBucket, RedisTTLStore, UniqueIdGenerator, claim_worker_id
from app.crawler import crawl
from app.crawlstore import CrawlStore
from app.db import SessionLocal
from app.infra import dependency_report, get_mongo_client, get_mongo_db, get_redis
from app.shardstore import MongoShardStore

SHARD_DB = "sis_verify"
SEED = "https://www.iana.org/"


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def main() -> int:
    report: dict[str, object] = {}

    section("1. Store handshake")
    report["stores"] = dependency_report()
    print(json.dumps(report["stores"], indent=2))

    section("2. PostgreSQL")
    with SessionLocal() as db:
        counts = db.execute(text(
            "select (select count(*) from students) students,"
            " (select count(*) from courses) courses,"
            " (select count(*) from course_offerings) offerings"
        )).one()
    report["postgres"] = dict(counts._mapping)
    print(report["postgres"])

    section("3. Redis rate limiter shared between two workers")
    redis = get_redis()
    ns = f"verify:{int(time.time())}"
    worker_a = RedisTokenBucket(redis, capacity=3, refill_per_second=0.001, key_prefix=ns)
    worker_b = RedisTokenBucket(redis, capacity=3, refill_per_second=0.001, key_prefix=ns)
    sequence = [worker_a.allow("client", now=1000.0) for _ in range(3)]
    second_worker = worker_b.allow("client", now=1000.0)
    report["rate_limiter"] = {
        "capacity": 3,
        "first_worker_grants": sum(sequence),
        "second_worker_granted": second_worker,
        "shared_bucket": second_worker is False,
    }
    print(report["rate_limiter"])

    section("4. Redis cache TTL and prefix invalidation")
    cache = RedisTTLStore(redis, key_prefix=ns)
    cache.set("autocomplete:cs:8", ["course-a"], ttl_seconds=1)
    ttl_before = redis.ttl(f"{ns}:autocomplete:cs:8")
    time.sleep(1.2)
    report["cache"] = {
        "ttl_seconds_seen": ttl_before,
        "value_after_expiry": cache.get("autocomplete:cs:8"),
    }
    print(report["cache"])

    section("5. ID worker slots are distinct")
    w1 = claim_worker_id(redis, key=f"{ns}:worker")
    w2 = claim_worker_id(redis, key=f"{ns}:worker")
    generator = UniqueIdGenerator(worker_id=w1)
    ids = [generator.next_id() for _ in range(1000)]
    report["id_generator"] = {
        "worker_a": w1, "worker_b": w2, "will_be_disjoint": w1 != w2,
        "batch_size": len(ids), "unique_in_batch": len(set(ids)),
    }
    print(report["id_generator"])

    section("6. MongoDB sharded cluster")
    client = get_mongo_client()
    client.drop_database(SHARD_DB)
    store = MongoShardStore(client, SHARD_DB)
    setup = store.ensure_sharded()
    for index in range(500):
        store.put(f"record-{index:04d}", {"index": index, "term": "2026-FA"})
    before = store.distribution()
    report["sharding"] = {
        "cluster": store.cluster_health(),
        "ensure": setup,
        "chunks": store.chunk_map(),
        "distribution_after_insert": before,
    }
    print(json.dumps({"shards": report["sharding"]["cluster"]["shards"],
                      "shard_key": setup["shard_key"],
                      "chunks": setup["chunks"],
                      "distribution": before["shards"]}, indent=2))

    section("7. Real chunk migration keeps every record readable")
    keys = store.key_range(limit=500)
    source, target = sorted(store.shards())[:2]
    moved = store.move_chunk(target, from_shard=source)
    after = store.distribution()
    readable = sum(1 for key in keys if store.get(key) is not None)
    report["chunk_migration"] = {
        "moved": moved,
        "distribution_before": before["shards"],
        "distribution_after": after["shards"],
        "records_checked": len(keys),
        "records_readable": readable,
        "no_data_lost": readable == len(keys) == before["total_documents"],
    }
    print(json.dumps(report["chunk_migration"], indent=2, default=str))

    section("8. Rebalance back to an even chunk split")
    balanced = store.rebalance()
    report["rebalance"] = balanced
    print(json.dumps(balanced["distribution"]["shards"], indent=2))

    section("9. Live crawl with a durable frontier")
    crawl_store = CrawlStore(get_mongo_db())
    crawl_store.init()
    crawl_store.reset(SEED)
    started = time.perf_counter()
    first = crawl(SEED, max_pages=5, store=crawl_store, delay=0.5)
    first_seconds = round(time.perf_counter() - started, 2)
    second = crawl(SEED, max_pages=5, store=crawl_store, delay=0.5)
    first_urls = {page["url"] for page in first["pages"]}
    second_urls = {page["url"] for page in second["pages"]}
    report["crawler"] = {
        "seed": SEED,
        "robots": first["robots"],
        "politeness_seconds": first["politeness_seconds"],
        "first_run": {
            "pages_crawled": first["pages_crawled"],
            "seconds": first_seconds,
            "errors": first["errors"],
            "titles": [page["title"] for page in first["pages"]][:5],
        },
        "second_run": {
            "pages_crawled": second["pages_crawled"],
            "resumed_from_frontier": second["resumed_from_frontier"],
            "urls_overlapping_first_run": len(first_urls & second_urls),
        },
        "store": crawl_store.stats(),
        # The second run must consume the persisted frontier and refetch nothing.
        "dedupe_proven": not (first_urls & second_urls) and second["pages_crawled"] >= 1,
    }
    print(json.dumps(report["crawler"], indent=2, default=str))

    out = Path(__file__).resolve().parents[1] / "docs" / "verification" / "stack_verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nWrote {out}")

    checks = [
        report["rate_limiter"]["shared_bucket"],
        report["cache"]["value_after_expiry"] is None,
        report["id_generator"]["unique_in_batch"] == 1000,
        report["sharding"]["cluster"]["is_mongos"],
        len(report["sharding"]["cluster"]["shards"]) >= 2,
        report["chunk_migration"]["no_data_lost"],
        report["crawler"]["first_run"]["pages_crawled"] >= 1,
        report["crawler"]["dedupe_proven"],
    ]
    print("\n\033[1mAll checks passed\033[0m" if all(checks) else "\n\033[1;31mSome checks failed\033[0m")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
