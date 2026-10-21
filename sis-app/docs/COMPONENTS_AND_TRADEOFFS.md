# Required system-design components

This prototype implements each assignment component as an explicit, observable experiment. Some are
intentionally single-process demonstrations; they are not eight independent microservices.

## Component-to-workload map

| Component | Implementation | Measurement / demonstration | Limitation |
|---|---|---|---|
| Rate limiter | Thread-safe token bucket in HTTP middleware | HTTP 429 count, request/error metrics | Process-local; not shared across replicas |
| Sharding | Synthetic key/value records stored in per-shard dictionaries | Record count per shard and orphaned keys | Not a PostgreSQL data-sharding implementation |
| Consistent hashing | SHA-256 ring with 100 virtual nodes per shard | Add-node experiment reports moved-key fraction | Routing does not migrate or replicate data |
| Key-value store | Bounded TTL + LRU cache for autocomplete | Hits, misses, item count, latency comparison | Process-local; cache can be stale for up to 20 s |
| Unique ID generator | Time-sortable 64-bit ID with worker ID and sequence | Batch size, unique-in-batch, total generated/collisions | Worker ID is fixed for the demo; multi-worker coordination absent |
| URL shortener | Random short code persisted in PostgreSQL | Create/redirect latency can be measured through Locust | No expiry, analytics, or abuse policy yet |
| Web crawler | Bounded public-HTTPS same-host crawler | Pages crawled, failures, frontier size, elapsed work | Not a general-purpose distributed crawler |
| Autocomplete | Course-code/title prefix query with TTL cache | p50/p95 and cache hit/miss counts | Prefix search only; no typo tolerance or relevance ranking |

## Key trade-offs
- **Correctness before caching:** cache only course suggestions. Seat availability and grades always use
  PostgreSQL transactional checks.
- **Bounded memory:** TTL/LRU limits cache growth; crawler caps page count, depth, response bytes and timeout.
- **Simple deployment:** modular monolith keeps the demo easy to run and observe. Split services only when
  independent scaling or fault isolation is supported by measurements.
- **Demonstration versus production:** sharding, consistent hashing, ID generation, rate limiting and cache
  are explicit teaching implementations. A real multi-instance deployment needs shared state, node health,
  migration/replication, worker-ID allocation, monitoring, and operational recovery.
- **Rate limiting is not admission correctness:** it controls request rate, not the seat invariant. The
  database still decides whether the final seat can be reserved.
- **Crawler safety:** only HTTPS URLs on public hosts are accepted; the crawler stays on the seed host,
  caps pages/depth/bytes and rejects credentials/private addresses. DNS rebinding remains a limitation
  of this coursework implementation; do not run it as a public arbitrary-URL fetch service.
