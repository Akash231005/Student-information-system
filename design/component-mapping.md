# Eight-Component Mapping

| Component | SIS use | Caveat | Measure |
|---|---|---|---|
| Rate limiter | Login, registration API, autocomplete | Does not prevent seat races | allowed/rejected count and overhead |
| Sharding | Student, enrollment, attendance and academic records | Cross-shard joins and skew | per-shard records, requests, latency |
| Consistent hashing | App/cache-node routing | No automatic data migration or failover | distribution and moved-key fraction |
| Key-value store | Course/timetable/profile read cache | Staleness and stampede | hit rate and hit/miss latency |
| Unique ID generator | Registration and notification IDs | Uniqueness assumptions | IDs/sec, collision count |
| URL shortener | Share public course resources | Open redirects and private links | redirect latency and invalid-link handling |
| Web crawler | Simulated resource listings | Unsafe URLs and duplicates | pages/min and extraction success |
| Autocomplete | Course code/title search | Privacy leakage | p95 latency and top-k accuracy |

## Implementation guidance
- Rate limiter: token bucket or sliding window; document per-process versus shared counters.
- Sharding: stable partition key, router, migration plan and verification.
- Consistent hashing: ring plus virtual nodes; compare with modulo hashing.
- Key-value store: cache-aside, TTL and invalidation; database remains authoritative.
- IDs: document concurrency/restart assumptions.
- URL shortener: validate schemes and reject unsafe destinations.
- Crawler: timeouts, fetch caps, deduplication and source timestamps.
- Autocomplete: normalized prefix matching, debounce, bounded results and authorization.

## Important distinctions
Rate limiting is not concurrency control. Consistent hashing is not replication. Updating a hash ring without moving records is not complete database re-sharding.
## Implemented prototype mapping (2026-10-19)

| Required component | Implemented path | Evidence |
|---|---|---|
| Rate limiter | FastAPI token-bucket middleware | 12-second Locust run: 83/401 requests rejected with 429; shows current bucket is restrictive |
| Sharding | In-memory synthetic key/value store | PUT/GET by routed key and per-shard record counts |
| Consistent hashing | Virtual-node SHA-256 ring | 1,000-key sample moved 277 keys after adding a fourth node |
| Key-value store | TTL/LRU cache on autocomplete | Cache enabled: p50/p95 4/6 ms; disabled: 7/15 ms in one short run each |
| Unique ID generator | Time/worker/sequence endpoint | Batch uniqueness endpoint and unit test |
| URL shortener | Random short codes and redirect endpoint | Create link + 307 redirect test |
| Web crawler | Bounded public HTTPS same-host crawler | Rejects private/non-HTTPS targets; live crawl must be bounded and network-enabled |
| Autocomplete | SQL prefix search + cache | Locust workload and cache-hit test |

These measurements are single short runs on one laptop and must not be described as general performance guarantees. The ring/shard store, cache, rate limiter, short-link store and metrics are process-local; PostgreSQL remains the authoritative academic data store.
