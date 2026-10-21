# Implementation status — 2026-10-19

> **Superseded in part.** The 21 October section at the end of this file records the migration of the
> lab components onto real Redis and a real MongoDB sharded cluster, and corrects the statements below
> that describe process-local state, simulated shards and an unverified crawler.

## Implemented

- FastAPI modular monolith, SQLAlchemy 2, PostgreSQL driver, Alembic migrations and browser dashboard.
- Student registration/login, PBKDF2 password hashing, signed bearer tokens, profile updates, role checks and record-level access control.
- Student, Course, CourseOffering, Enrollment, AttendanceRecord, Assessment, Grade, TimetableEvent, AcademicNotification and UserAccount models.
- Course search/autocomplete, offering discovery, enrollment/drop/re-enrollment, student profile/enrollment/grade reads, attendance, assessments, timetable and notifications.
- Atomic conditional seat reservation, transactional enrollment insert, idempotency keys and partial unique index for one active enrollment per student/offering.
- Token-bucket rate limiter, TTL/LRU autocomplete cache, consistent-hash ring, in-memory shard simulation, time-sortable ID generator, PostgreSQL-backed short links, bounded HTTPS crawler and component/HTTP metrics.
- Deterministic synthetic data generator, Locust workloads for search/profile/writes/autocomplete/short-link redirects, and PostgreSQL concurrency tests.
- Professional reference scan, source-level enrollment review, architecture/component docs, system-design report, 9-slide presentation, A3 poster, demo script and submission checklist.

## Verified locally

- PostgreSQL-backed automated suite: **23 passed**.
- Ruff: passed.
- Alembic upgrade + schema check passed on fresh temporary SQLite and PostgreSQL 17 databases.
- PostgreSQL capacity race: 20 distinct students contend for 5 seats; exactly 5 succeed, 15 receive HTTP 409, and counter equals active enrollment rows.
- Concurrent duplicate-request test leaves exactly one active enrollment and one counter increment.
- Drop/re-enroll test verifies a seat is released once and a new idempotency key permits re-enrollment.
- Synthetic benchmark dataset generated: 1,000 students, 100 courses and 200 offerings.
- API health, dashboard, API docs, and component metrics routes return HTTP 200.

## Saved 20-second Locust baseline

All baseline runs used 10 users, spawn rate 2 users/s, PostgreSQL 17 and synthetic data. Rate limiting was disabled except for the explicit overload run. The results are local single-run observations, not production capacity claims.

| Workload | Requests | Throughput | p50 | p95 | Failures |
|---|---:|---:|---:|---:|---:|
| Course discovery | 681 | 35.82 req/s | 5 ms | 10 ms | 0 |
| Authenticated profile/grades/enrollments/timetable reads | 669 | 35.27 req/s | 5 ms | 12 ms | 0 |
| Student registration writes | 370 | 19.47 req/s | 60 ms | 83 ms | 0 |
| Autocomplete cache enabled | 675 | 35.55 req/s | 2 ms | 5 ms | 0 |
| Autocomplete cache disabled | 659 | 34.68 req/s | 5 ms | 10 ms | 0 |
| Course-search overload with rate limiter enabled | 676 | 35.61 req/s | 4 ms | 10 ms | 243 HTTP 429 |

Cache-on mean latency was 2.88 ms versus 5.85 ms with cache disabled. The overload run rejected 243/676 requests (35.95%); this shows admission control, but the configured quota is restrictive for that traffic mix and needs tuning.

## Limitations and next steps

- Staff mutations and student self-record reads enforce role/scope checks. Token revocation/refresh and production identity integration are absent; do not expose publicly or use real student data.
- Rate limiter, cache, shard records, ID worker and metrics are process-local. Short-link mappings persist in PostgreSQL.
- Consistent hashing changes routing but does not migrate/replicate records; the shard store does not shard PostgreSQL.
- The crawler is bounded and same-host HTTPS only. Live DNS fetch could not be verified because DNS resolution was unavailable in this environment; positive parser/frontier behavior is covered with a mocked response.
- A separate API-process sample observed ~7.4% average CPU of one logical CPU (sampled peak 16%) and ~90.7 MiB RSS; this is not continuous peak telemetry or total host/database usage.
- The cache and rate-limit measurements are one short run per condition. Repeat runs at longer durations and capture API/PostgreSQL/load-generator resources before making scaling claims.
- Add token revocation/refresh, shared Redis coordination, waitlist/outbox lifecycle, real shard migration/replication, crawler SSRF/DNS-pinning hardening and CI concurrency tests before any production-like deployment.

---

# Implementation status — 2026-10-21 (supersedes the limitations above)

The lab components were moved out of the API process and onto real services. The earlier sections are
kept as the record of what was true on 19 October; the statements they make about process-local state,
simulated shards and an unverified crawler no longer describe the code.

## What changed

- **Redis 7 is now required shared state.** The token bucket is a Lua script in Redis
  (`RedisTokenBucket`), the autocomplete cache is `SETEX` with `SCAN`-based prefix invalidation
  (`RedisTTLStore`), and the ID generator's worker slot comes from `INCR mod 1024`. The in-memory
  `TokenBucketRateLimiter`, `TTLKeyValueStore` and per-process worker counter were deleted.
- **MongoDB 7 sharded cluster is now required.** `mongos` router (27017) + config-server replica set
  (27019) + `sis-shard-a` (27021) and `sis-shard-b` (27022). Collection `sharded_records` is sharded on
  `{_id: "hashed"}`. `app/shardstore.py` performs real `chunk_map`, `owner_of` (via `explain`),
  `move_chunk` (explicit bounds — hashed keys reject `find`) and `rebalance`.
- **The in-memory shard suggestion was deleted.** The consistent-hash ring survives as real routing math
  and is now printed *next to* the router's answer, so a disagreement is visible instead of hidden.
- **The crawler was rebuilt.** robots.txt with RFC 9309 semantics, per-host `Crawl-delay` pacing,
  429/503 retry honouring `Retry-After`, gzip handling, cross-host redirect refusal, a durable frontier
  and page store in MongoDB, bounded attempts, and deduplication keyed on the *requested* URL.
- **No fallback path.** `app/infra.py` raises at startup if Redis or `mongos` is unreachable, and
  `/health` returns 503 listing the failing store. The app cannot silently degrade to local dictionaries.
- `scripts/start_stack.sh` brings the whole stack up idempotently; `scripts/verify_stack.py` measures it
  and writes `sis-app/docs/verification/stack_verification.json`.

## Verified on 2026-10-21

| Check | Result |
|---|---|
| Automated suite | **37 passed, 2 skipped** (PostgreSQL race test needs an explicit `DATABASE_URL`; live crawl is opt-in) |
| Ruff | passed |
| Stores | Redis 7.4.11, MongoDB 7.0.45 through `mongos` (`isdbgrid`), PostgreSQL 17 |
| Rate limiter across processes | capacity 3 spent by worker A; worker B refused |
| Cache TTL | present at TTL 1 s, `None` after expiry |
| ID worker slots | two distinct slots claimed; 1,000 generated IDs, 1,000 unique |
| Sharding | 500 records → 249/251 across two shards, 3 chunks each |
| `moveChunk` | 129/371 after the move; all 500 keys still readable; no data lost |
| Rebalance | 256/244, 3 chunks per shard |
| Live crawl | `www.iana.org` robots parsed, 5 pages stored, 1 page rejected at the 1 MB cap |
| Crawl resume | second run took 5 URLs from the persisted frontier and refetched none |

## Still true, and still limitations

- Redis and the MongoDB members are single nodes on one host: shared, not highly available.
- The consistent-hash ring is a startup snapshot; `mongos` owns placement and reacts immediately, the
  ring catches up on restart.
- The Locust baseline above predates the Redis migration and used the in-memory cache. It has not been
  re-run; the Redis cache is verified functionally, not re-benchmarked.
- The crawler is same-host, serial and single-process by design. DNS rebinding is still not defended
  against; do not run it as a public arbitrary-URL fetch service.
- Rate limiting still controls request rate, not the seat invariant — PostgreSQL remains the correctness
  boundary for enrollment.
