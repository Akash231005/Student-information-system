# Scalable Student Information System

A coursework prototype for the System Design Laboratory assignment. It combines a working academic
workflow with measurable demonstrations of the required system-design components.

## Features

- Student registration, login, signed bearer tokens, role checks, and record-level access control.
- Course catalog/search and term/section-specific course offerings.
- Transaction-safe enrollment, seat capacity, idempotency keys, drop/re-enroll lifecycle.
- Attendance, assessments, grades, timetable events, and student notifications.
- Staff dashboard forms plus an interactive OpenAPI reference.
- Redis-backed token-bucket rate limiter, Redis TTL cache, consistent-hash ring, a **real MongoDB
  sharded cluster** (mongos + config server + two shard replica sets) holding sharded records, a
  time-sortable ID generator with worker slots claimed in Redis, persistent short links, and a bounded
  HTTPS crawler with a durable frontier.
- Locust workloads, PostgreSQL concurrency tests, Alembic migrations, and performance results.

## Architecture and evidence

- [Architecture](docs/ARCHITECTURE.md)
- [Component mapping and trade-offs](docs/COMPONENTS_AND_TRADEOFFS.md)
- [Performance evaluation](docs/PERFORMANCE_EVALUATION.md)
- [Demo / setup runbook](docs/DEMO_RUNBOOK.md)
- [Stack verification output](docs/verification/stack_verification.json) — measured, not described

The distinguishing engineering thesis is **correctness under concurrent registration plus measured
architectural trade-offs**. The shared-state components run against real services rather than
dictionaries in the API process: Redis for the limiter, cache and worker slots, and a two-shard MongoDB
cluster for sharded records. The prototype still does not claim production availability — each of those
services is a single node on one host.
## Quick start

Requires Python 3.11+, `uv`, and Podman. PostgreSQL is not enough: the app exits at startup if Redis or
`mongos` is unreachable.

```bash
cd ~/Documents/SIS-Karpathy-Map/sis-app
uv sync --extra test --extra benchmark --extra dev --extra deliverables

# PostgreSQL + Redis + MongoDB sharded cluster (idempotent, prints the cluster state)
bash scripts/start_stack.sh

cp .env.example .env   # only if .env does not already exist
# On a brand-new empty database, apply migrations (do not run on a pre-existing create_all DB).
uv run alembic upgrade head
uv run python -m scripts.generate_dataset --students 1000 --courses 100 --offerings-per-course 2
uv run python -m scripts.create_staff --email staff@example.test --student-number STAFF001
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the dashboard at http://127.0.0.1:8000/ or API docs at http://127.0.0.1:8000/docs. Register a
student account in the dashboard. Use the staff account for course/offering setup, attendance, grades,
timetable, notifications, shard operations, and the crawler.

## Tests and code quality
```bash
# IMPORTANT: integration tests drop/recreate tables; use a dedicated test database.
DATABASE_URL='postgresql+psycopg://sis:sis_dev_only@localhost:5432/sis' \
  SIS_RATE_LIMIT_ENABLED=false uv run pytest -q          # 37 passed, 2 skipped
uv run ruff check app tests scripts migrations

# Proof against the live services, written to docs/verification/stack_verification.json
uv run python scripts/verify_stack.py

# Opt-in: crawl a real site (the suite never touches a third-party site by default)
SIS_LIVE_CRAWL=1 uv run pytest tests/test_crawler.py -q
```

The PostgreSQL integration suite includes a race test in which 20 students contend for 5 seats;
exactly 5 enrollments succeed. SQLite can run quick tests, but is not evidence of PostgreSQL
concurrency correctness. The two skipped tests are deliberate: the race test needs an explicitly
provided `DATABASE_URL`, and the live crawl is opt-in.

## Important prototype limitations

- Use synthetic data only; do not put real student records or passwords into this coursework demo.
- Set a strong `SIS_TOKEN_SECRET` and `SIS_ENV=production` in any production-like deployment.
- Redis, `mongos` and PostgreSQL are single nodes on one host. State is shared between app processes,
  but nothing survives the loss of that host, and there is no replication or failover.
- The consistent-hash ring is a startup snapshot of the shard set. Adding a shard changes placement in
  `mongos` immediately; the ring agrees again after a restart. It routes, it never moves data —
  `moveChunk` does.
- The crawler honours robots.txt and `Crawl-delay`, stays on the seed host, refuses cross-host
  redirects and caps pages/depth/attempts/bytes, but is not a hardened public arbitrary-URL fetch service.
- Performance results are short, local, 10-user experiments; they are not a production capacity claim,
  and the cache-on/cache-off rows predate the Redis migration.

## Submission artifacts

The report, presentation, poster, demo script and submission ZIP are maintained in the parent project’s `deliverables/` directory. See `../README.md` for the map and build commands. To rebuild the PDF/PPTX outputs, install the optional `deliverables` extra and run the generator scripts from the parent directory.
