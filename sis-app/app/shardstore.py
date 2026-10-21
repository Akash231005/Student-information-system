"""Sharded record store on a real MongoDB sharded cluster.

Topology (started by `scripts/start_stack.sh`):

    mongos (27017)
      ├── configsvr replica set  (27019)  - chunk metadata
      ├── shard-a replica set    (27021)  - data
      └── shard-b replica set    (27022)  - data

The collection is sharded on `{_id: "hashed"}`, so the record key *is* the shard key.
mongos owns chunk placement; this module never writes to a shard directly. Everything it
reports - which shard owns a key, how many documents and chunks sit on each shard - comes
from the cluster itself (`explain`, `collStats`, `config.chunks`), not from a local model.
"""
from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import OperationFailure

COLLECTION = "sharded_records"
# Quarter points of the signed 64-bit hash space; splitting the initial chunk here gives
# four chunks that spread evenly across two shards without waiting for the balancer.
HASH_SPLITS = (-(2**62), 0, 2**62)


class MongoShardStore:
    def __init__(self, client: MongoClient, db_name: str = "sis"):
        self.client = client
        self.db: Database = client[db_name]
        self.collection = self.db[COLLECTION]
        self.namespace = f"{db_name}.{COLLECTION}"

    # ------------------------------------------------------------------ topology

    def is_mongos(self) -> bool:
        return self.client.admin.command("hello").get("msg") == "isdbgrid"

    def shards(self) -> list[str]:
        reply = self.client.admin.command("listShards")
        return sorted(shard["_id"] for shard in reply.get("shards", []))

    def config_servers(self) -> list[str]:
        reply = self.client.admin.command("listShards")
        return sorted(
            member["host"]
            for shard in reply.get("shards", [])
            for member in [shard] if not shard.get("_id", "").startswith("shard")
        )

    def shard_key(self) -> dict[str, Any] | None:
        doc = self.client["config"]["collections"].find_one({"_id": self.namespace})
        return None if doc is None or doc.get("dropped") else doc.get("key")

    def is_sharded(self) -> bool:
        return self.shard_key() is not None

    def collection_uuid(self) -> Any | None:
        """MongoDB 6+ keys chunk metadata by collection UUID instead of namespace."""
        doc = self.client["config"]["collections"].find_one({"_id": self.namespace})
        return None if doc is None else doc.get("uuid")

    def _chunk_query(self) -> dict[str, Any]:
        uuid = self.collection_uuid()
        if uuid is None:
            raise LookupError(f"{self.namespace} is not sharded yet")
        return {"uuid": uuid}

    def ensure_sharded(self) -> dict[str, Any]:
        """Enable sharding, shard the collection on a hashed _id and pre-split it.

        Idempotent: re-running against an already-sharded collection only tops up the
        chunk splits, so the API can call it on every startup.
        """
        self.client.admin.command("enableSharding", self.db.name)
        if not self.is_sharded():
            self.client.admin.command(
                "shardCollection", self.namespace, key={"_id": "hashed"}
            )
        split = self._split_chunks()
        return {
            "namespace": self.namespace,
            "shard_key": self.shard_key(),
            "shards": self.shards(),
            "chunks": self.chunk_count(),
            "splits_performed": split,
        }

    def _split_chunks(self) -> int:
        performed = 0
        for value in HASH_SPLITS:
            try:
                self.client.admin.command("split", self.namespace, middle={"_id": value})
                performed += 1
            except OperationFailure:
                # Already a boundary, outside the current chunk, or not splittable.
                continue
        return performed

    def chunk_count(self) -> int:
        if not self.is_sharded():
            return 0
        return self.client["config"]["chunks"].count_documents(self._chunk_query())

    def chunk_map(self) -> list[dict[str, Any]]:
        if not self.is_sharded():
            return []
        cursor = self.client["config"]["chunks"].find(
            self._chunk_query(), {"min": 1, "max": 1, "shard": 1, "jumbo": 1}
        ).sort("min", ASCENDING)
        return [
            {
                "min": _render(doc.get("min")),
                "max": _render(doc.get("max")),
                "shard": doc["shard"],
                "jumbo": doc.get("jumbo", False),
            }
            for doc in cursor
        ]

    def distribution(self) -> dict[str, Any]:
        """Per-shard document and chunk counts, straight from the cluster."""
        counts = self.collection.aggregate(
            [{"$collStats": {"storageStats": {}}}, {"$group": {
                "_id": "$shard", "docs": {"$sum": "$storageStats.count"}}}]
        )
        docs = {row["_id"]: row["docs"] for row in counts}
        chunks: dict[str, int] = {}
        if self.is_sharded():
            chunks = {
                row["_id"]: row["n"]
                for row in self.client["config"]["chunks"].aggregate([
                    {"$match": self._chunk_query()},
                    {"$group": {"_id": "$shard", "n": {"$sum": 1}}},
                ])
            }
        return {
            "namespace": self.namespace,
            "total_documents": self.count(),
            "shards": {
                name: {"documents": docs.get(name, 0), "chunks": chunks.get(name, 0)}
                for name in self.shards()
            },
        }

    def owner_of(self, key: str) -> str | None:
        """Which shard mongos routes this key to. Authoritative, from the query planner."""
        explain = self.db.command(
            "explain", {"find": COLLECTION, "filter": {"_id": key}}, verbosity="queryPlanner"
        )
        return _first_shard_name(explain)

    def move_chunk(self, to_shard: str, from_shard: str | None = None) -> dict[str, Any]:
        """Migrate one real chunk. Hashed keys require explicit bounds, not a find filter."""
        query: dict[str, Any] = {"$and": [self._chunk_query()]}
        if from_shard:
            query["$and"].append({"shard": from_shard})
        chunk = self.client["config"]["chunks"].find_one(query)
        if chunk is None:
            raise LookupError(f"no chunk to migrate from {from_shard or 'any shard'}")
        if chunk["shard"] == to_shard:
            raise ValueError(f"chunk already lives on {to_shard}")
        self.client.admin.command({
            "moveChunk": self.namespace,
            "bounds": [chunk["min"], chunk["max"]],
            "to": to_shard,
            "_waitForDelete": True,
        })
        return {
            "moved_bounds": {"min": _render(chunk["min"]), "max": _render(chunk["max"])},
            "from_shard": chunk["shard"],
            "to_shard": to_shard,
        }

    def rebalance(self) -> dict[str, Any]:
        """Move chunks off overloaded shards until every shard holds an even share."""
        names = self.shards()
        if len(names) < 2 or not self.is_sharded():
            return {"moves": [], "note": "fewer than two shards registered"}
        moves: list[dict[str, Any]] = []
        for _ in range(self.chunk_count()):
            per_shard = {name: 0 for name in names}
            for row in self.client["config"]["chunks"].aggregate([
                {"$match": self._chunk_query()},
                {"$group": {"_id": "$shard", "n": {"$sum": 1}}},
            ]):
                per_shard[row["_id"]] = row["n"]
            busiest = max(per_shard, key=lambda name: per_shard[name])
            quietest = min(per_shard, key=lambda name: per_shard[name])
            if per_shard[busiest] - per_shard[quietest] <= 1:
                break
            try:
                moves.append(self.move_chunk(quietest, from_shard=busiest))
            except (LookupError, ValueError, OperationFailure) as exc:
                return {"moves": moves, "stopped": str(exc)[:200]}
        return {"moves": moves, "distribution": self.distribution()}

    # ---------------------------------------------------------------------- data

    def put(self, key: str, value: dict[str, Any]) -> dict[str, Any]:
        self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
        return {"key": key, "shard": self.owner_of(key), "stored": True}

    def get(self, key: str) -> dict[str, Any] | None:
        doc = self.collection.find_one({"_id": key})
        return None if doc is None else doc.get("value")

    def delete(self, key: str) -> bool:
        return self.collection.delete_one({"_id": key}).deleted_count == 1

    def count(self) -> int:
        return self.collection.count_documents({})

    def key_range(self, limit: int = 1000) -> list[str]:
        return [doc["_id"] for doc in self.collection.find({}, {"_id": 1}).limit(limit)]

    def cluster_health(self) -> dict[str, Any]:
        hello = self.client.admin.command("hello")
        # `hello().me` is undefined on a mongos-only cluster; fall back to the address this
        # process actually dialled rather than printing "unknown".
        address = self.client.address
        router = hello.get("me") or (f"{address[0]}:{address[1]}" if address else None)
        return {
            "router": router,
            "is_mongos": hello.get("msg") == "isdbgrid",
            "server_version": self.client.server_info().get("version"),
            "shards": self.shards(),
            "shard_key": self.shard_key(),
            "chunks": self.chunk_count(),
            "balancer_mode": self._balancer_mode(),
        }

    def _balancer_mode(self) -> str:
        try:
            return self.client.admin.command("balancerStatus").get("mode", "unknown")
        except OperationFailure:
            return "unknown"


def _render(value: Any) -> Any:
    """BSON MinKey/MaxKey/Int64 are not JSON-serialisable; show them readably."""
    name = type(value).__name__
    if name in {"MinKey", "MaxKey"}:
        return "-inf" if name == "MinKey" else "+inf"
    if isinstance(value, dict):
        return {key: _render(item) for key, item in value.items()}
    return value


def _first_shard_name(explain: dict[str, Any]) -> str | None:
    """Pull the targeted shard out of a sharded explain, tolerating server versions."""
    stack: list[Any] = [explain]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if isinstance(node.get("shardName"), str):
                return node["shardName"]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None
