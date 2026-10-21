# Orbit SIS — real infrastructure migration

**Date:** 21 October 2026
**Commit scope:** `sis-app/` backend, tests, docs, verification evidence
**Status:** implemented, verified, and shut down. Nothing is left running.

---

## 1. What this phase changed

The previous build demonstrated the eight required system-design components with dictionaries inside the
API process. That is a demonstration of an algorithm, not of a system: two app processes each had their own
token bucket, their own cache, and their own idea of which "shard" owned a key. Three components were
labelled "simulation" in the documentation, and the crawler had only ever been tested against a mocked
HTTP response.

This phase replaced them with real services and deleted the fallbacks.

| Component | Before | After |
|---|---|---|
| Rate limiter | `TokenBucketRateLimiter`, per-process dict + lock | `RedisTokenBucket` — the entire read-modify-write is one Lua script |
| Autocomplete cache | `TTLKeyValueStore`, per-process dict + lock | `RedisTTLStore` — `SETEX` with `SCAN`-based prefix invalidation |
| ID worker ID | Fixed constant for the demo | `claim_worker_id()` — `INCR mod 1024` in Redis |
| Sharding | "Synthetic in-memory shard buckets" | Real MongoDB sharded cluster; `explain` for ownership, `moveChunk` for movement, real rebalance |
| Consistent hashing | The only routing answer | Kept as routing math, now printed **beside** the router's authoritative answer |
| Web crawler | Bounded fetch, mocked-network test only | robots.txt (RFC 9309), `Crawl-delay` pacing, 429/503 retry with `Retry-After`, gzip, cross-host redirect refusal, durable frontier and page store in MongoDB, requested-URL deduplication, bound on attempts |
| Startup | Silent fallback if state was unavailable | **Refuses to start**; `/health` returns 503 naming the failed store |

There is no in-memory fallback path left in the code. The classes were deleted, not disabled, so the
application cannot quietly degrade to per-process state.

---

## 2. Technology and why

| Service | Version | Role | Why this one |
|---|---|---|---|
| Redis | 7.4.11 (`redis:7-alpine`) | Token buckets, TTL cache, ID worker slots | A single Lua script gives atomicity without a distributed lock, and the container is a few MB. `--maxmemory 128mb --maxmemory-policy allkeys-lru --save '' --appendonly no` — this is volatile shared state, so persistence is deliberately off |
| MongoDB | 7.0.45 (`mongo:7.0`) | Sharded records and the crawl frontier | The assignment's sharding component needs real chunk metadata and real migration; a sharded cluster is the honest way to show both |
| PostgreSQL | 17 (`postgres:17-alpine`) | Authoritative academic records | Unchanged. Still the only correctness boundary for enrollment |
| Podman | rootless | Runs every container | No passwordless sudo on this host, so no system packages; images and `uv` only |
| FastAPI / SQLAlchemy / pymongo 4.19 / redis-py 6.4 | — | Application | `pymongo` and `redis` were the only new dependencies |

### Cluster topology

| Process | Port | Config |
|---|---|---|
| `sis-postgres` | 5432 | existing volume, reattached |
| `sis-redis` | 6379 | 128 MB cap, `allkeys-lru`, no persistence |
| `sis-mongo-cfg` | 27019 | `--configsvr --replSet sis-cfg` |
| `sis-mongo-a` | 27021 | `--shardsvr --replSet sis-shard-a` |
| `sis-mongo-b` | 27022 | `--shardsvr --replSet sis-shard-b` |
| `sis-mongos` | 27017 | `--configdb sis-cfg/127.0.0.1:27019` |

Every `mongod` runs `--wiredTigerCacheSizeGB 0.25`, the server minimum, because the whole cluster is sized
for an 8 GB laptop. All containers use `--network=host`: rootless podman's `pasta` backend cannot publish
ports on this host, so port mapping never worked and host networking was the only option that did.

`sis-app/scripts/start_stack.sh` creates, starts, initialises and reports the entire stack idempotently.

### Data location — read this before touching the containers

The data lives in **anonymous podman volumes**, not named ones. `podman stop` and `podman start` preserve
it; `podman rm` destroys it. The PostgreSQL volume is
`d9cbd8ec8d5eb265eeb3a782c1402477062b6f6af6cf21f91fc5b22871276b6b` (mounted at
`/var/lib/postgresql/data`) and the verification database's is
`859b6ab1d2785a4a937735ac376d922b21b0731b42f430b68820981d3dc4d691`. Do not delete those containers.

---

## 3. Design decisions worth defending

**The collection is sharded on `{_id: "hashed"}`.** That makes the record key the shard key, so a single
lookup is answered by exactly one shard instead of being scattered to all of them. The alternative —
sharding on a low-cardinality field like term — would have produced hot shards and a scatter-gather read
path, which is the failure mode a sharding exercise is supposed to teach you to avoid.

**Two answers for placement, on purpose.** Deleting the consistent-hash ring would have thrown away the
component under study; trusting it would have been wrong once `mongos` exists. `GET
/system-design/route/{key}` therefore returns `ring_prediction` and `actual_owner` side by side with an
`agrees` flag. Disagreement is a visible fact rather than an averaged-away one.

**`moveChunk` needed explicit bounds.** A hashed shard key cannot be moved by a range `find`, which is what
the obvious implementation would have used. The working call passes `{min: {_id: <val>}, max: {...}}`.
Recorded here because it cost real debugging time.

**`config.chunks` is keyed by collection `uuid`, not `ns`.** MongoDB 6 and later; a `ns` query silently
returns zero rows, which looks exactly like "no sharding happened".

**The crawler is serial per host by design.** Intra-host parallelism is the specific thing `Crawl-delay`
exists to prevent, so a worker pool would have been a contradiction, not an optimisation.

**Deduplication keys on the requested URL, not the final URL.** The first version stored pages under their
post-redirect URL, so the next run re-fetched every URL that redirected. Catching this required the
resume test to assert on the *set* of URLs rather than the count.

**`close_dependencies()` runs from `atexit`, not the ASGI lifespan.** The clients are process-wide; closing
them per lifespan broke repeated `TestClient` contexts in the suite.

---

## 4. Verification

Every number below was measured on this host against the running services. Raw output:
`sis-app/docs/verification/stack_verification.json`, `startup_refusal.txt`, `http_*.json`.

### The stack

| Check | Result |
|---|---|
| Automated suite | **37 passed, 2 skipped** (`uv run pytest`) |
| Ruff | **passed** (`app`, `tests`, `scripts`) |
| Redis | 7.4.11, `allkeys-lru`, 128 MB cap |
| MongoDB | 7.0.45, `isdbgrid: true`, router `127.0.0.1:27017` |
| PostgreSQL | 17, dataset regenerated to 1,001 students / 102 courses / 200 offerings |

### The components

| Check | Observed | Establishes |
|---|---|---|
| Rate limiter shared across processes | worker A spent all 3 tokens of capacity 3; worker B refused at the same timestamp | one allowance, not one per process |
| Cache TTL | key present at TTL 1 s, `None` after expiry | server-side expiry, not a dict |
| ID worker slots | claims returned slots 1 and 2; 1,000 IDs generated, 1,000 unique | concurrent processes cannot share a slot |
| Shard distribution | 500 records → 249 / 251, 3 chunks per shard | `mongos` really splits the data |
| `moveChunk` | 129 / 371 documents, 2 / 4 chunks | real data movement |
| Post-migration readability | all 500 keys still readable, count unchanged | no data lost |
| Rebalance | 256 / 244, 3 chunks per shard | the balancer restores an even split |
| Live crawl | `www.iana.org`, robots parsed, 5 pages stored, 1 page rejected at the 1 MB cap | the network path works against a real host |
| Crawl resume | second run took 5 URLs off the persisted frontier, refetched 0 | durable frontier and working dedupe |

### The hard requirement: no silent fallback

`startup_refusal.txt` records both cases:

```
$ SIS_REDIS_URL=redis://127.0.0.1:6399/0 uvicorn app.main:app --port 8011
RuntimeError: Required state stores are not available:
  - Redis unreachable at redis://127.0.0.1:6399/0: Error 111 connecting to 127.0.0.1:6399. Connection refused.
Start the stack with `bash scripts/start_stack.sh` from the repository root.
ERROR:    Application startup failed. Exiting.
```

and the same for an unreachable `mongos`. The app does not start, rather than starting and pretending.

### HTTP surface

| Endpoint | Status | Payload |
|---|---|---|
| `/health` | 200 | store versions, `is_mongos: true` |
| `/system-design/shards` | 200 | 2 shards, `{_id: hashed}`, 6 chunks, `balancer_mode: full` |
| `/system-design/route/record-0001` | 200 | `ring_prediction: sis-shard-a`, `actual_owner: sis-shard-a`, `agrees: true` |
| `/system-design/metrics` | 200 | limiter `shared by every app process`, cache `Redis TTL cache`, ID `worker id reserved in Redis`, live cluster state |
| `/system-design/crawler/state` | 200 | 8 pages, 50 frontier rows, 12 recorded runs |
| `/system-design/sharded-records` | 200 | live distribution |

---

## 5. What this does not prove

- **Availability.** Redis and every MongoDB member are single nodes on one host, unreplicated. State is
  shared between app processes; it does not survive the loss of the host. No failover, no backup, no ops
  story.
- **A current cache benchmark.** The Locust cache-on/cache-off rows in `PERFORMANCE_EVALUATION.md` were
  measured against the in-process LRU cache, which no longer exists, and `SIS_CACHE_ENABLED` is gone. They
  are retained and labelled as historical. The Redis cache is verified functionally, not re-benchmarked.
- **A distributed crawler.** Same host, serial, single process. DNS rebinding is still not defended
  against, so it must not be exposed as a public arbitrary-URL fetch service.
- **Sharded academic records.** PostgreSQL still holds students, courses, enrollments and grades. Sharding
  applies to `sharded_records`, the component's own collection. Nothing measured justified sharding the
  academic tables.
- **That the test suite is safe to run against a real database.** It drops and recreates tables. Running it
  against the dev database wiped the synthetic dataset during this phase; it was regenerated afterwards.
  A guard in `tests/conftest.py` that refuses to run destructively unless the database name looks like a
  test database is the obvious next step and is *not* implemented.

---

## 6. Operating it

```bash
cd ~/Documents/SIS-Karpathy-Map/sis-app

bash scripts/start_stack.sh                    # bring everything up (idempotent)
uv run python scripts/verify_stack.py          # measure the whole thing
uv run pytest -q                               # 37 passed, 2 skipped
SIS_LIVE_CRAWL=1 uv run pytest tests/test_crawler.py -q   # opt-in live crawl
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

To stop, without losing data:

```bash
podman stop sis-mongos sis-mongo-a sis-mongo-b sis-mongo-cfg sis-redis sis-verify-pg sis-postgres
```

`start_stack.sh` brings them all back. Do **not** `podman rm` them; the volumes are anonymous and would go
with the containers.

---

## 7. State at hand-off

Everything was shut down after verification. No service is running.

| Container | State |
|---|---|
| `sis-mongos` | Exited (137 — SIGKILL on stop; stateless, no data of its own) |
| `sis-mongo-a`, `sis-mongo-b`, `sis-mongo-cfg` | Exited (0) |
| `sis-redis` | Exited (0) |
| `sis-postgres`, `sis-verify-pg` | Exited (0) |
| API (`uvicorn`, port 8000) | stopped, port closed |

All containers still exist with their volumes attached. `bash scripts/start_stack.sh` returns the cluster
to the state described in section 4, and `scripts/verify_stack.py` re-measures it.

---

## 8. Files that carry this work

| Path | What it is |
|---|---|
| `sis-app/app/infra.py` | Lazy clients, `dependency_report()` (the refusal), `atexit` cleanup |
| `sis-app/app/components.py` | Redis token bucket, Redis TTL store, worker-slot claim, hash ring, ID generator |
| `sis-app/app/shardstore.py` | `ensure_sharded`, `chunk_map`, `owner_of` via `explain`, `move_chunk`, `rebalance`, `distribution` |
| `sis-app/app/crawlstore.py` | Durable frontier, page store, run log |
| `sis-app/app/crawler.py` | robots.txt, pacing, retry, gzip, redirect policy, dedupe, attempt budget |
| `sis-app/app/extended.py` | All rewired endpoints, `init_backends()`, live metrics |
| `sis-app/scripts/start_stack.sh` | Idempotent full-stack bring-up |
| `sis-app/scripts/verify_stack.py` | Measures every claim, writes the JSON evidence |
| `sis-app/tests/test_sharding.py` | Real-cluster assertions (migration, readability, distribution) |
| `sis-app/tests/test_components.py` | Cross-process limiter sharing, TTL, worker slots, 40-thread burst |
| `sis-app/tests/test_crawler.py` | Scripted robots/policy tests + opt-in live crawl |
| `sis-app/docs/verification/` | `stack_verification.json`, `startup_refusal.txt`, `http_*.json` |
| `sis-app/docs/*.md` | Architecture, components, performance, runbook — all rewritten to match reality |
