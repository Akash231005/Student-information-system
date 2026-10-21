# System-Design Fundamentals

## Transactions and concurrency
Capacity check plus enrollment insert must be safe as one operation. Use row locking or atomic conditional updates, a transaction and a unique enrollment constraint.
https://www.postgresql.org/docs/16/transaction-iso.html
https://www.postgresql.org/docs/17/explicit-locking.html

## Idempotency
A timeout does not prove a write failed. Use idempotency keys or unique constraints so retries do not duplicate side effects.

## Sharding
Partitioning splits a logical table. Sharding places partitions on separate nodes. State which model the prototype implements. Choose keys from query patterns and explain cross-shard queries.
https://www.postgresql.org/docs/current/ddl-partitioning.html

## Consistent hashing
A ring usually limits key remapping when nodes join/leave. It does not migrate data, replicate records, detect failures or preserve transactions automatically. Use virtual nodes and measure skew and movement.
https://research.google/pubs/consistent-hashing-with-bounded-loads/

## Cache-aside
Read cache first, database on miss, then set TTL. Invalidate affected keys after writes. The database remains authoritative for grades and registrations.
https://redis.io/docs/latest/develop/use-cases/cache-aside/

## Rate limiting
Protect login, search and write endpoints. Return HTTP 429 with retry guidance. Rate limiting does not enforce course capacity or guarantee fairness.
https://redis.io/docs/latest/develop/use-cases/rate-limiter/

## Search, IDs and crawler
Debounce autocomplete, cap results and authorize every result. Use UUID/database IDs unless a custom generator is required. Crawler needs timeouts, deduplication, fetch limits and source timestamps.

## Observability
Measure throughput, mean/p95 latency, errors, CPU, memory, DB connections, cache hit rate, per-shard counts and correctness violations.
https://docs.locust.io/en/2.20.2/what-is-locust.html
https://opentelemetry.io/docs/concepts/signals/metrics/