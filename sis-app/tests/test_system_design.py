from fastapi.testclient import TestClient

from app.main import app


def test_id_metrics_and_pure_ring_movement_experiment():
    with TestClient(app) as client:
        before = client.get("/system-design/ring").json()
        ids = client.get("/system-design/ids", params={"count": 25})
        assert ids.status_code == 200
        assert ids.json()["count"] == 25
        assert ids.json()["unique_in_batch"] is True
        assert ids.json()["ids_per_second"] > 0
        assert ids.json()["elapsed_ms"] >= 0
        assert len(set(ids.json()["ids"])) == 25
        assert all(isinstance(value, str) for value in ids.json()["ids"])

        moved = client.post("/system-design/ring/experiment", params={
            "node": "experiment-node", "key_count": 500,
        })
        assert moved.status_code == 200
        data = moved.json()
        assert data["keys_sampled"] == 500
        assert 0 < data["moved_fraction"] < 1
        after = client.get("/system-design/ring").json()
        assert after["nodes"] == before["nodes"]

        metrics = client.get("/system-design/metrics").json()
        assert metrics["id_generator"]["generated"] >= 25
        assert len(metrics["consistent_hashing"]["nodes"]) == before["nodes"]
