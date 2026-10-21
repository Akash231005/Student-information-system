# Demo runbook

## 1. Start the database

Install Podman and make sure its service/machine is running. Start PostgreSQL 17:

```bash
podman run -d --name sis-postgres \
  -e POSTGRES_DB=sis -e POSTGRES_USER=sis \
  -e POSTGRES_PASSWORD=sis_dev_only \
  -p 5432:5432 docker.io/library/postgres:17-alpine
```

If the container already exists, use `podman start sis-postgres`. Confirm readiness:

```bash
podman exec sis-postgres pg_isready -U sis -d sis
```

The credentials above are for local coursework only. Do not expose port 5432 to a public network.

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
SIS_RATE_LIMIT_ENABLED=false SIS_CACHE_ENABLED=false \
  uv run uvicorn app.main:app --port 8001
SIS_RATE_LIMIT_ENABLED=false SIS_CACHE_ENABLED=true \
  uv run uvicorn app.main:app --port 8002
```

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

Keep output prefixes unique per run. The crawler has a mocked success-path unit test; live crawling
could not be validated in this environment because DNS resolution was unavailable.
