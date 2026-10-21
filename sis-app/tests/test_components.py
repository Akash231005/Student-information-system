"""Tests for the shared-state components.

Redis is a hard dependency, so these tests connect to the real instance rather than
skipping: use `bash scripts/start_stack.sh` first. Each test gets its own key namespace,
so a stale bucket from an earlier run can never make a later run pass.
"""
import time
import uuid

import pytest

from app.components import (
    ConsistentHashRing,
    RedisTokenBucket,
    RedisTTLStore,
    UniqueIdGenerator,
    claim_worker_id,
)
from app.infra import get_redis


@pytest.fixture
def redis():
    client = get_redis()
    client.ping()
    return client


@pytest.fixture
def ns():
    return f"test:{uuid.uuid4().hex[:8]}"


def test_token_bucket_rejects_then_refills(redis, ns):
    limiter = RedisTokenBucket(redis, capacity=2, refill_per_second=1, key_prefix=ns)
    assert limiter.allow("student-1", now=10.0)
    assert limiter.allow("student-1", now=10.0)
    assert not limiter.allow("student-1", now=10.0)
    assert limiter.allow("student-1", now=11.0)


def test_token_bucket_is_shared_between_workers(redis, ns):
    # Two limiter instances stand in for two app processes behind one bucket: the second
    # consumer must see the token the first already spent.
    worker_a = RedisTokenBucket(redis, capacity=1, refill_per_second=0.001, key_prefix=ns)
    worker_b = RedisTokenBucket(redis, capacity=1, refill_per_second=0.001, key_prefix=ns)
    assert worker_a.allow("client", now=100.0)
    assert not worker_b.allow("client", now=100.0)


def test_concurrent_spends_never_exceed_capacity(redis, ns):
    from concurrent.futures import ThreadPoolExecutor

    limiter = RedisTokenBucket(redis, capacity=5, refill_per_second=0.001, key_prefix=ns)
    with ThreadPoolExecutor(max_workers=8) as pool:
        granted = list(pool.map(lambda _: limiter.allow("burst", now=500.0), range(40)))
    assert sum(granted) == 5


def test_ttl_cache_expiry_is_managed_by_redis(redis, ns):
    cache = RedisTTLStore(redis, key_prefix=ns)
    cache.set("k", {"v": 1}, ttl_seconds=1)
    assert cache.get("k") == {"v": 1}
    assert 0 < redis.ttl(f"{ns}:k") <= 1
    time.sleep(1.1)
    assert cache.get("k") is None


def test_ttl_cache_prefix_invalidation(redis, ns):
    cache = RedisTTLStore(redis, key_prefix=ns)
    cache.set("courses:1", ["A"], ttl_seconds=60)
    cache.set("courses:2", ["B"], ttl_seconds=60)
    cache.set("other:1", {"x": 1}, ttl_seconds=60)
    assert cache.invalidate_prefix("courses:") == 2
    assert cache.get("courses:2") is None
    assert cache.get("other:1") == {"x": 1}


def test_worker_ids_are_distinct_across_processes(redis, ns):
    key = f"{ns}:worker"
    assert claim_worker_id(redis, key=key) != claim_worker_id(redis, key=key)


def test_consistent_hash_ring_routes_and_node_removal():
    ring = ConsistentHashRing(["a", "b", "c"], replicas=50)
    before = {key: ring.route(key) for key in (f"student-{i}" for i in range(100))}
    ring.add_node("d")
    after = {key: ring.route(key) for key in before}
    moved = sum(before[key] != after[key] for key in before)
    assert 0 < moved < len(before)
    ring.remove_node("d")
    assert ring.node_count() == 3


def test_id_generator_unique_in_batch():
    generator = UniqueIdGenerator(worker_id=3)
    ids = [generator.next_id() for _ in range(100)]
    assert len(ids) == len(set(ids))
