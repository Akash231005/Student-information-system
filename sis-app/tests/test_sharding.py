"""Sharded-record tests against the real MongoDB sharded cluster.

These assert cluster behaviour, not a Python model: the assertions read chunk metadata from
the config server and document counts from `$collStats`, which is what mongos actually did.
"""
import pytest

from app.infra import get_mongo_client
from app.shardstore import MongoShardStore

TEST_DB = "sis_sharding_test"


@pytest.fixture(scope="module")
def store():
    client = get_mongo_client()
    assert client.admin.command("hello").get("msg") == "isdbgrid", "mongos must be the router"
    shard_store = MongoShardStore(client, TEST_DB)
    shard_store.collection.drop()
    shard_store.ensure_sharded()
    for index in range(200):
        shard_store.put(f"key-{index:03d}", {"index": index})
    yield shard_store
    client.drop_database(TEST_DB)


def test_collection_is_sharded_on_a_hashed_key(store):
    assert store.shard_key() == {"_id": "hashed"}
    assert len(store.shards()) >= 2
    assert store.chunk_count() >= 2


def test_chunks_are_spread_over_every_shard(store):
    per_shard = store.distribution()["shards"]
    assert sum(row["chunks"] for row in per_shard.values()) == store.chunk_count()
    assert all(row["chunks"] > 0 for row in per_shard.values())


def test_documents_land_on_the_shard_mongos_reports(store):
    distribution = store.distribution()
    assert distribution["total_documents"] == 200
    occupied = [name for name, row in distribution["shards"].items() if row["documents"] > 0]
    assert len(occupied) == len(store.shards())
    for key in ("key-000", "key-077", "key-199"):
        assert store.owner_of(key) in store.shards()


def test_chunk_migration_moves_documents_and_keeps_them_readable(store):
    before = store.distribution()
    source, target = sorted(before["shards"])[:2]
    keys = store.key_range(limit=200)

    moved = store.move_chunk(target, from_shard=source)

    assert moved["from_shard"] == source
    assert moved["to_shard"] == target
    after = store.distribution()
    assert after["shards"][source]["chunks"] == before["shards"][source]["chunks"] - 1
    assert after["shards"][target]["chunks"] == before["shards"][target]["chunks"] + 1
    assert after["total_documents"] == before["total_documents"]
    assert all(store.get(key) is not None for key in keys)


def test_rebalance_evens_out_the_chunk_counts(store):
    result = store.rebalance()
    assert "distribution" in result
    counts = [row["chunks"] for row in result["distribution"]["shards"].values()]
    assert max(counts) - min(counts) <= 1
