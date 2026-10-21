# Demo runbook

## 1. Start the state stores

The app needs three stores: PostgreSQL (records), Redis (shared limiter/cache/worker slots) and a
MongoDB sharded cluster (sharded records, crawl frontier). It refuses to start without them, so this
step is not optional.

```bash
cd ~/Documents/SIS-Karpathy-Map/sis-app
bash scripts/start_stack.sh
```

The script is idempotent: it starts existing containers, creates missing ones, initialises the replica
sets, and registers both shards. It prints the cluster state at the end. Expected ports on loopback:

| Service | Port |
|---|---|
| PostgreSQL | 5432 |
| Redis | 6379 |
| mongos (router — the app's `SIS_MONGO_URI`) | 27017 |
| config server | 27019 |
| shard `sis-shard-a` / `sis-shard-b` | 27021 / 27022 |

Every container uses `--network=host`; rootless podman's `pasta` backend cannot publish ports on this
host. Confirm the cluster:

```bash
podman exec sis-postgres pg_isready -U sis -d sis
podman exec sis-redis redis-cli ping
podman exec sis-mongos mongosh --quiet --eval 'db.adminCommand({listShards:1})'
```

The credentials in `.env.example` are for local coursework only. Do not expose these ports publicly.

## 2. Configure and install

```bash
cd ~/Documents/SIS-Karpathy-Map/sis-app
uv sync --extra test --extra benchmark --extra dev
cp .env.example .env   # only if .env does not already exist
```
Edit `.env` and set a random secret for local tokens, for example with
`openssl rand -hex 32`. Keep `.env` out of Git. For a clean database, apply migrations:

```bash
uv run alembic upgrade head
uv run python -m scripts.generate_dataset --students 1000 --courses 100 --offerings-per-course 2
```

Create a staff account interactively (the password is not placed in shell history):

```bash
uv run python -m scripts.create_staff --email staff@example.test --student-number STAFF001
```

## 3. Start and use the app

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Dashboard: http://127.0.0.1:8000/
- Interactive API reference: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Register a student account through the dashboard, then log in. To create courses/offerings or record
attendance, grades, timetable entries and notifications, log in with the staff account created above.
## 4. Tests

Use a dedicated development/test database. The integration tests drop and recreate tables; **never
point them at a production or shared database**.

```bash
DATABASE_URL='postgresql+psycopg://sis:sis_dev_only@localhost:5432/sis' \
  SIS_RATE_LIMIT_ENABLED=false uv run pytest -q
uv run ruff check app tests scripts migrations
DATABASE_URL='sqlite:////tmp/sis_migration_check.db' uv run alembic upgrade head
DATABASE_URL='sqlite:////tmp/sis_migration_check.db' uv run alembic check
```

The PostgreSQL concurrency test is intentionally skipped unless `DATABASE_URL` is explicitly set
in the process environment to PostgreSQL. SQLite is not evidence of PostgreSQL concurrency safety.

## 5. Load tests
Start the API with a controlled flag set. Use the same dataset, duration, user count, spawn rate
and workload for comparisons:

```bash
SIS_RATE_LIMIT_ENABLED=false uv run uvicorn app.main:app --port 8001
SIS_RATE_LIMIT_ENABLED=true  uv run uvicorn app.main:app --port 8002
```

Both instances share one Redis allowance, so the limiter-enforced run is enforced across *both*
processes, not per process.

In another terminal, compare autocomplete:

```bash
uv run locust -f locust_autocomplete.py --headless --host http://127.0.0.1:8001 \
  -u 10 -r 2 -t 60s --csv results/cache-off
uv run locust -f locust_autocomplete.py --headless --host http://127.0.0.1:8002 \
  -u 10 -r 2 -t 60s --csv results/cache-on
```

Use `locust_course_search.py`, `locust_profile_reads.py`, and `locust_student_writes.py` for
search, authenticated reads, and registration writes. For short-link creation/redirect latency, copy
a staff bearer token from the dashboard or `/auth/login` response and run:

```bash
SIS_STAFF_TOKEN='<staff bearer token>' uv run locust -f locust_short_links.py \
  --headless --host http://127.0.0.1:8001 -u 10 -r 2 -t 60s --csv results/short-links
```

Keep output prefixes unique per run.

## 6. Prove the real components

One command exercises every real backend and writes the measurements to
`docs/verification/stack_verification.json`:

```bash
uv run python scripts/verify_stack.py
```

It checks: the store handshake, PostgreSQL row counts, a token bucket shared between two limiter
instances, cache TTL expiry, distinct ID worker slots, 500 records split across both Mongo shards, a
chunk migration that keeps every record readable, a rebalance, and a live crawl of `www.iana.org`
followed by a second run that resumes the persisted frontier without refetching anything.

The crawler's live test is opt-in so the suite never hits a third-party site by default:

```bash
SIS_LIVE_CRAWL=1 uv run pytest tests/test_crawler.py -q
```

## 7. Demonstrate sharding from the API

With the API running and a staff token:

```bash
curl -s localhost:8000/system-design/shards
curl -s localhost:8000/system-design/route/record-0001   # ring answer vs mongos answer
curl -s -X POST localhost:8000/system-design/shards/move-chunk -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"to_shard":"sis-shard-b","from_shard":"sis-shard-a"}'
curl -s -X POST localhost:8000/system-design/shards/rebalance -H "Authorization: Bearer $TOKEN"
curl -s localhost:8000/system-design/crawler/state
```

`/health` returns 200 only when all three stores answer, and 503 with the failing store listed
otherwise — the app is not "up" if its shared state is gone.

## 8. Adding a third shard

```bash
podman run -d --name sis-mongo-c --network=host docker.io/library/mongo:7.0 \
  mongod --shardsvr --replSet sis-shard-c --port 27023 --bind_ip 127.0.0.1 \
  --dbpath /data/db --wiredTigerCacheSizeGB 0.25
podman exec sis-mongo-c mongosh --quiet --port 27023 --eval \
  "rs.initiate({_id:'sis-shard-c',members:[{_id:0,host:'127.0.0.1:27023'}]})"
podman exec sis-mongos mongosh --quiet --eval "sh.addShard('sis-shard-c/127.0.0.1:27023')"
```

`mongos` starts balancing onto the new shard immediately. The consistent-hash ring is a snapshot taken
at startup (`init_backends()`), so restart the API to rebuild it from the live shard set; until you do,
`/system-design/route/{key}` shows the ring still placing keys across two nodes while the router reports
three, which is the disagreement the endpoint exists to expose. After the restart the ring reports three
nodes and `POST /system-design/shards/rebalance` moves data across all three.
