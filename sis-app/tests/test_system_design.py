"""API-level tests for the sharding and routing surface against the real cluster."""
from fastapi.testclient import TestClient

from app.main import app


def test_ring_experiment_reports_key_movement():
    with TestClient(app) as client:
        response = client.post("/system-design/ring/experiment",
                               params={"node": "test-shard", "key_count": 100})
        assert response.status_code == 200
        data = response.json()
        assert data["keys_sampled"] == 100
        assert 0 <= data["rerouted_fraction"] <= 1
        assert data["nodes_after"] >= data["nodes_before"]


def test_route_endpoint_compares_the_ring_with_mongos():
    with TestClient(app) as client:
        body = client.get("/system-design/route/some-key").json()
        assert body["ring_prediction"] in body["nodes"]
        assert body["actual_owner"] in body["nodes"]


def test_sharded_record_roundtrip_and_distribution():
    with TestClient(app) as client:
        shards = set(client.get("/system-design/shards").json()["shards"])
        put = client.put("/system-design/sharded-records/api-test-key", json={"value": 42})
        assert put.status_code == 200
        assert put.json()["stored"] is True
        assert put.json()["shard"] in shards

        got = client.get("/system-design/sharded-records/api-test-key")
        assert got.status_code == 200
        assert got.json()["value"] == {"value": 42}
        assert got.json()["shard"] == put.json()["shard"]

        distribution = client.get("/system-design/sharded-records").json()
        assert distribution["distribution"]["total_documents"] >= 1
        assert set(distribution["distribution"]["shards"]) == shards
        assert set(distribution["ring_prediction"]) <= set(client.get(
            "/system-design/ring").json()["node_names"])


def test_shard_cluster_health_reports_the_real_topology():
    with TestClient(app) as client:
        health = client.get("/system-design/shards").json()
        assert health["is_mongos"] is True
        assert len(health["shards"]) >= 2
        assert health["shard_key"] == {"_id": "hashed"}
        assert health["chunks"] >= 2


def test_health_endpoint_reports_both_stores():
    with TestClient(app) as client:
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["stores"]["redis"]["version"]
        assert body["stores"]["mongodb"]["is_mongos"] is True
