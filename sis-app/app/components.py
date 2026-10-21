"""Small, independently testable implementations of required system-design components.

These are teaching/measurement implementations, not claims of production-grade distributed
coordination. In-memory state is process-local and must not be mistaken for a cluster-wide
rate limiter or durable cache.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any


class TokenBucketRateLimiter:
    """Thread-safe per-process token bucket; distributed mode needs shared atomic storage."""
    def __init__(self, capacity: int = 20, refill_per_second: float = 5.0):
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("capacity and refill rate must be positive")
        self.capacity = capacity
        self.refill_rate = refill_per_second
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            tokens, updated = self._buckets.get(key, (float(self.capacity), now))
            tokens = min(float(self.capacity), tokens + max(0.0, now - updated) * self.refill_rate)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1.0, now)
            return True


class TTLKeyValueStore:
    """Bounded in-process TTL key-value cache with LRU eviction."""
    def __init__(self, max_items: int = 1000):
        self.max_items = max_items
        self._items: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str, now: float | None = None) -> Any | None:
        now = time.monotonic() if now is None else now
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires, value = item
            if expires <= now:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl_seconds: float = 30, now: float | None = None) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = time.monotonic() if now is None else now
        with self._lock:
            self._items[key] = (now + ttl_seconds, value)
            self._items.move_to_end(key)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [key for key in self._items if key.startswith(prefix)]
            for key in keys:
                del self._items[key]
            return len(keys)


class ConsistentHashRing:
    """Virtual-node hash ring for experiments; routing does not itself move/replicate data."""
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


class UniqueIdGenerator:
    """Time-sortable 64-bit IDs; suitable for a single process in this prototype only."""
    def __init__(self, worker_id: int = 1, epoch_ms: int = 1_700_000_000_000):
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


def verify_url_signature(url: str, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), url.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@dataclass
class ComponentMetrics:
    allowed: int = 0
    rejected: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
