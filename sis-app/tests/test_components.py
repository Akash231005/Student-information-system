from app.components import (
    ConsistentHashRing,
    TokenBucketRateLimiter,
    TTLKeyValueStore,
    UniqueIdGenerator,
)


def test_token_bucket_rejects_then_refills():
    limiter = TokenBucketRateLimiter(capacity=2, refill_per_second=1)
    assert limiter.allow("student-1", now=10)
    assert limiter.allow("student-1", now=10)
    assert not limiter.allow("student-1", now=10)
    assert limiter.allow("student-1", now=11)


def test_ttl_cache_expiry_and_prefix_invalidation():
    cache = TTLKeyValueStore(max_items=2)
    cache.set("courses:1", ["A"], ttl_seconds=5, now=10)
    assert cache.get("courses:1", now=12) == ["A"]
    assert cache.get("courses:1", now=15) is None
    cache.set("courses:2", ["B"], now=20)
    cache.set("courses:3", ["C"], now=20)
    assert cache.invalidate_prefix("courses:") == 2


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

from fastapi.testclient import TestClient

from app.main import app


def test_ring_experiment_reports_key_movement():
    with TestClient(app) as client:
        response = client.post("/system-design/ring/experiment",
                               params={"node": "test-shard", "key_count": 100})
        assert response.status_code == 200
        data = response.json()
        assert data["keys_sampled"] == 100
        assert 0 <= data["moved_fraction"] <= 1
        assert data["nodes_after"] >= data["nodes_before"]
