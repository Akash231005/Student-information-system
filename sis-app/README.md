# Scalable Student Information System

A coursework prototype for the System Design Laboratory assignment. It combines a working academic
workflow with measurable demonstrations of the required system-design components.

## Features

- Student registration, login, signed bearer tokens, role checks, and record-level access control.
- Course catalog/search and term/section-specific course offerings.
- Transaction-safe enrollment, seat capacity, idempotency keys, drop/re-enroll lifecycle.
- Attendance, assessments, grades, timetable events, and student notifications.
- Staff dashboard forms plus an interactive OpenAPI reference.
- Token-bucket rate limiter, TTL/LRU autocomplete cache, consistent-hash ring, synthetic shard store,
  time-sortable ID generator, persistent short links, and a bounded HTTPS crawler.
- Locust workloads, PostgreSQL concurrency tests, Alembic migrations, and performance results.

## Architecture and evidence

- [Architecture](docs/ARCHITECTURE.md)
- [Component mapping and trade-offs](docs/COMPONENTS_AND_TRADEOFFS.md)
- [Performance evaluation](docs/PERFORMANCE_EVALUATION.md)
- [Demo / setup runbook](docs/DEMO_RUNBOOK.md)

The distinguishing engineering thesis is **correctness under concurrent registration plus measured
architectural trade-offs**. The prototype deliberately avoids claiming that an in-memory shard ring,
cache, or rate limiter is a production distributed system.
## Quick start

Requires Python 3.11+, `uv`, and Podman (or a PostgreSQL 17 server).

```bash
cd ~/Documents/SIS-Karpathy-Map/sis-app
uv sync --extra test --extra benchmark --extra dev --extra deliverables
# Start PostgreSQL as shown in docs/DEMO_RUNBOOK.md, then configure .env.
# On a brand-new empty database, apply migrations (do not run on a pre-existing create_all DB).
uv run alembic upgrade head
uv run python -m scripts.generate_dataset --students 1000 --courses 100 --offerings-per-course 2
uv run python -m scripts.create_staff --email staff@example.test --student-number STAFF001
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the dashboard at http://127.0.0.1:8000/ or API docs at http://127.0.0.1:8000/docs.
Register a student account in the dashboard. Use the staff account for course/offering setup,
attendance, grades, timetable, and notification management.

## Tests and code quality
```bash
# IMPORTANT: integration tests drop/recreate tables; use a dedicated test database.
DATABASE_URL='postgresql+psycopg://sis:sis_dev_only@localhost:5432/sis' \
  SIS_RATE_LIMIT_ENABLED=false uv run pytest -q
uv run ruff check app tests scripts migrations
```

The PostgreSQL integration suite includes a race test in which 20 students contend for 5 seats;
exactly 5 enrollments succeed. SQLite can run quick tests, but is not evidence of PostgreSQL
concurrency correctness.

## Important prototype limitations

- Use synthetic data only; do not put real student records or passwords into this coursework demo.
- Set a strong `SIS_TOKEN_SECRET` and `SIS_ENV=production` in any production-like deployment.
- The rate limiter and autocomplete cache are process-local. A multi-replica service needs shared
  atomic state or a deliberately accepted per-replica quota.
- Shard routing is a simulation: node add/remove does not migrate or replicate stored data.
- The crawler is bounded and restricted, but is not a hardened public arbitrary-URL fetch service.
- Performance results are short, local, 10-user experiments; they are not a production capacity claim.

## Submission artifacts

The report, presentation, poster, demo script and submission ZIP are maintained in the parent project’s `deliverables/` directory. See `../README.md` for the map and build commands. To rebuild the PDF/PPTX outputs, install the optional `deliverables` extra and run the generator scripts from the parent directory.
