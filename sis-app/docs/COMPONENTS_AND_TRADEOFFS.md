# Required system-design components

This prototype implements each assignment component as an explicit, observable experiment. Every
component below runs against a real backing service — Redis 7, or a two-shard MongoDB 7 cluster — so
the behaviour it demonstrates is produced by that service, not by a dictionary in the API process.
They are still not eight independent microservices.

## Component-to-workload map

| Component | Implementation | Measurement / demonstration | Limitation |
|---|---|---|---|
| Rate limiter | Token bucket held in Redis, read-modify-write inside one Lua script | HTTP 429 count; a burst from N processes still spends from one allowance | One Redis instance, no replication or Redis Cluster; a Redis outage degrades to 503, not to unlimited traffic |
| Sharding | Real MongoDB sharded cluster: `mongos` + config server + two shard replica sets, collection sharded on `{_id: "hashed"}` | Documents and chunks per shard; `explain` reports the owning shard; `moveChunk` with explicit bounds | Two shards on one host, single-member replica sets: no host-level HA, no zone tagging |
| Consistent hashing | SHA-256 ring, 100 virtual nodes per shard, built from the live shard set | Add/remove-node experiment reports the moved-key fraction; ring placement is returned next to `mongos`'s answer | The ring is routing math only. It does not move data — `moveChunk` does |
| Key-value store | Redis `SETEX` TTL cache for autocomplete | Hits, misses, item count, TTL, latency delta | Single Redis node with `allkeys-lru` and a 128 MB cap; entries can be evicted before their TTL |
| Unique ID generator | Time-sortable 64-bit ID (timestamp + worker + sequence); worker slot claimed with `INCR mod 1024` in Redis | Batch size, unique-in-batch, total generated, collisions | Worker slots are leased, not released; a process restart burns a slot. Clock rollback inside one process is detected by the sequence, not by an external clock service |
| URL shortener | Random short code persisted in PostgreSQL | Create/redirect latency can be measured through Locust | No expiry, analytics, or abuse policy yet |
| Web crawler | robots.txt (RFC 9309) + `Crawl-delay` pacing, retry on 429/503 with `Retry-After`, gzip, durable frontier in MongoDB | Pages crawled, errors, frontier size, politeness seconds, and a second run that resumes the frontier instead of refetching | Same-host, same-process, serial by design; not a distributed crawler and not a hardened arbitrary-URL fetch service |
| Autocomplete | Course-code/title prefix query with a Redis TTL cache | p50/p95 and cache hit/miss counts | Prefix search only; no typo tolerance or relevance ranking |

## Key trade-offs
- **Correctness before caching:** cache only course suggestions. Seat availability and grades always use
  PostgreSQL transactional checks.
- **Bounded memory:** the Redis instance is capped at 128 MB with `allkeys-lru`; the crawler caps page
  count, depth, attempts, response bytes and timeout.
- **Simple deployment:** modular monolith keeps the demo easy to run and observe. Split services only when
  independent scaling or fault isolation is supported by measurements.
- **Real services, honest limits:** the rate limiter, cache, worker-slot allocation and sharded record
  store now live in services that outlive the API process, which is what makes multi-process behaviour
  correct. Availability is still single-host: losing the Redis container or the `mongos` container takes
  the feature down rather than failing over. Region-aware shard keys, replication across hosts, and a
  Redis Cluster are the next steps, not current claims.
- **Two answers for placement:** the consistent-hash ring and `mongos` are both real, and they can
  disagree. The route endpoint returns both on purpose; the router's answer wins for reads and writes.
- **Rate limiting is not admission correctness:** it controls request rate, not the seat invariant. The
  database still decides whether the final seat can be reserved.
- **Crawler safety:** only HTTPS URLs on public hosts are accepted; the crawler stays on the seed host,
  honours robots.txt and `Crawl-delay`, refuses cross-host redirects, caps pages/depth/attempts/bytes and
  rejects credentials and private addresses. DNS rebinding remains a limitation of this coursework
  implementation; do not run it as a public arbitrary-URL fetch service.
