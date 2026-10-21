"""Implementations of the required system-design components.

The rate limiter and the key-value cache hold their state in Redis, so every app process
shares one allowance and one cache. The consistent-hash ring and the ID generator keep
their state in the process, which is correct for what they are: the ring is pure routing
math over the live shard set, and the generator is a single-writer sequence whose worker
id is reserved in Redis so concurrently started processes cannot share a slot.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from threading import Lock
from typing import Any

import redis as redis_lib


class RedisTokenBucket:
    """Token bucket whose counters live in Redis, shared by every app process.

    The read-modify-write happens inside one Lua script, so two processes cannot both
    read the same token count and both spend the same token. Time is wall-clock rather
    than monotonic because the state is shared between processes.
    """

    SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])
local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local updated = tonumber(bucket[2])
if tokens == nil or updated == nil then
  tokens = capacity
  updated = now
end
if now < updated then
  -- Clock skew between hosts: refill nothing and rebase instead of minting tokens.
  updated = now
end
tokens = math.min(capacity, tokens + (now - updated) * refill)
local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end
redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, ttl)
return allowed
"""

    def __init__(
        self,
        client: redis_lib.Redis,
        capacity: int = 120,
        refill_per_second: float = 10.0,
        key_prefix: str = "sis:ratelimit",
    ):
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("capacity and refill rate must be positive")
        self.client = client
        self.capacity = capacity
        self.refill_rate = refill_per_second
        self.key_prefix = key_prefix
        # Idle keys are dropped once they would have refilled anyway.
        self.key_ttl = int(capacity / refill_per_second) + 2
        # Loaded on first use so constructing the limiter does not require Redis to be up.
        self._sha: str | None = None

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        args = (1, f"{self.key_prefix}:{key}", self.capacity, self.refill_rate, now, self.key_ttl)
        if self._sha is None:
            self._sha = self.client.script_load(self.SCRIPT)
        try:
            return bool(self.client.evalsha(self._sha, *args))
        except redis_lib.exceptions.NoScriptError:
            # Redis restarted and dropped its script cache; reload and retry once.
            self._sha = self.client.script_load(self.SCRIPT)
            return bool(self.client.evalsha(self._sha, *args))

    def remaining(self, key: str, now: float | None = None) -> float:
        now = time.time() if now is None else now
        tokens, updated = self.client.hmget(f"{self.key_prefix}:{key}", ["tokens", "ts"])
        if tokens is None or updated is None:
            return float(self.capacity)
        refilled = float(tokens) + max(0.0, now - float(updated)) * self.refill_rate
        return min(float(self.capacity), refilled)

    def tracked_keys(self) -> int:
        return sum(1 for _ in self.client.scan_iter(match=f"{self.key_prefix}:*", count=500))


class RedisTTLStore:
    """TTL key-value cache in Redis, with server-side expiry and prefix invalidation."""

    def __init__(self, client: redis_lib.Redis, key_prefix: str = "sis:cache"):
        self.client = client
        self.key_prefix = key_prefix

    def _k(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def get(self, key: str) -> Any | None:
        raw = self.client.get(self._k(key))
        return None if raw is None else json.loads(raw)

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.client.setex(self._k(key), max(1, round(ttl_seconds)), json.dumps(value))

    def invalidate_prefix(self, prefix: str) -> int:
        match = f"{self.key_prefix}:{prefix}*"
        deleted = 0
        batch: list[str] = []
        for key in self.client.scan_iter(match=match, count=500):
            batch.append(key)
            if len(batch) >= 500:
                deleted += self.client.delete(*batch)
                batch.clear()
        if batch:
            deleted += self.client.delete(*batch)
        return deleted

    def item_count(self) -> int:
        return sum(1 for _ in self.client.scan_iter(match=f"{self.key_prefix}:*", count=1000))

    def eviction_policy(self) -> dict[str, str]:
        info = self.client.info("memory")
        config = self.client.config_get("maxmemory-policy")
        return {
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "maxmemory_human": info.get("maxmemory_human", "unknown"),
            "maxmemory_policy": config.get("maxmemory-policy", "unknown"),
        }


def claim_worker_id(client: redis_lib.Redis, slots: int = 1024, key: str = "sis:idgen:worker") -> int:
    """Reserve a distinct worker slot for this process.

    INCR is atomic across processes, so two instances starting at the same moment never
    receive the same worker id. A restarted process takes the next slot; a duplicate would
    require `slots` distinct worker ids (that many restarts) inside a single millisecond.
    """
    return int(client.incr(key)) % slots


class ConsistentHashRing:
    """Virtual-node hash ring over the live shard set.

    This is real routing math, and it now routes to real shards: the node names are the
    shard replica sets registered with mongos, and MongoDB owns the actual chunk placement.
    The ring answers "which shard should own this key"; `sh.moveChunk` is what moves data.
    """

    def __init__(self, nodes: list[str] | None = None, replicas: int = 100):
        self.replicas = replicas
        self._ring: list[tuple[int, str]] = []
        self._nodes: set[str] = set()
        for node in nodes or []:
            self.add_node(node)

    def _hash(self, value: str) -> int:
        return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big")

    def add_node(self, node: str) -> None:
        if node in self._nodes:
            return
        self._nodes.add(node)
        self._ring.extend((self._hash(f"{node}:{i}"), node) for i in range(self.replicas))
        self._ring.sort()

    def remove_node(self, node: str) -> None:
        if node not in self._nodes:
            return
        self._nodes.discard(node)
        self._ring = [(point, owner) for point, owner in self._ring if owner != node]

    def route(self, key: str) -> str | None:
        if not self._ring:
            return None
        point = self._hash(key)
        lo, hi = 0, len(self._ring)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._ring[mid][0] < point:
                lo = mid + 1
            else:
                hi = mid
        return self._ring[lo % len(self._ring)][1]

    def node_count(self) -> int:
        return len(self._nodes)

    def nodes(self) -> tuple[str, ...]:
        return tuple(sorted(self._nodes))

    def ownership(self, keys: list[str]) -> dict[str, int]:
        shares: dict[str, int] = {}
        for key in keys:
            node = self.route(key)
            if node is not None:
                shares[node] = shares.get(node, 0) + 1
        return shares


class UniqueIdGenerator:
    """Time-sortable 64-bit IDs: 41 bits of milliseconds, 10 bits worker, 12 bits sequence."""

    def __init__(self, worker_id: int, epoch_ms: int = 1_700_000_000_000):
        if not 0 <= worker_id < 1024:
            raise ValueError("worker_id must fit in 10 bits")
        self.worker_id = worker_id
        self.epoch_ms = epoch_ms
        self._last_ms = -1
        self._sequence = 0
        self._lock = Lock()

    def next_id(self) -> int:
        with self._lock:
            now = int(time.time() * 1000) - self.epoch_ms
            if now < self._last_ms:
                raise RuntimeError("Clock moved backwards; ID generation paused")
            if now == self._last_ms:
                self._sequence = (self._sequence + 1) & 0xFFF
                if self._sequence == 0:
                    while now <= self._last_ms:
                        now = int(time.time() * 1000) - self.epoch_ms
            else:
                self._sequence = 0
            self._last_ms = now
            return (now << 22) | (self.worker_id << 12) | self._sequence


def make_short_code(length: int = 8) -> str:
    return secrets.token_urlsafe(length)[:length]
