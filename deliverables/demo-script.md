# Live Demo Script (6–8 minutes)

## Before the demo
1. Start Podman PostgreSQL and confirm it is healthy.
2. From sis-app, run the PostgreSQL suite against the dedicated coursework database: DATABASE_URL='postgresql+psycopg://sis:sis_dev_only@localhost:5432/sis' SIS_RATE_LIMIT_ENABLED=false uv run pytest -q.
3. Start the API with SIS_RATE_LIMIT_ENABLED=false uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 for baseline/demo.
4. Create a synthetic staff account with uv run python -m scripts.create_staff --email staff@example.test --student-number STAFF001. Enter the password at the prompt, then log in and use /docs Authorize for staff-only endpoints.
5. Open the dashboard at http://127.0.0.1:8000/ and API explorer at /docs.
6. Keep the PostgreSQL concurrent test output available.

## Demo sequence

### 1. Student workflow (60–90 seconds)
- Register a synthetic student with an example.test email.
- Log in and show the short-lived bearer token flow and /auth/me.
- Search course catalog and list course offerings.

### 2. Enrollment correctness (90 seconds)
- Enroll the student into an OPEN offering.
- Retry the same request with the same idempotency key and explain retry semantics.
- Attempt enrollment after capacity is exhausted; show HTTP 409.
- Show the PostgreSQL concurrency test: capacity 5, 20 simultaneous students, exactly 5 successful enrollments.

### 3. Academic records (60 seconds)
- Record attendance for an enrolled student; show duplicate session rejection.
- Create an assessment, enter a grade and show max-marks validation.
- Show timetable and notification endpoints.

### 4. Required system-design components (2 minutes)
- Course autocomplete: call /autocomplete twice and inspect MISS then HIT.
- Rate limiter and latency metrics: /system-design/http-metrics.
- Consistent hash: route a stable key, add a node, route again.
- Shard store: write/read a synthetic key and show per-shard counts.
- Unique IDs, short URL and bounded crawler: use /docs examples.

### 5. Performance and trade-offs (60–90 seconds)
- Show the separate Locust CSV files and compare p50/p95/throughput/error rate.
- Explain which state is PostgreSQL-authoritative and which is shared through Redis or the MongoDB sharded cluster.
- Explicitly state the limitations: role/self-access checks are implemented, but token revocation/refresh and production identity controls are absent; Redis and the MongoDB members are single unreplicated nodes on one host; short links persist in PostgreSQL; academic records are not sharded — only the component's own collection is.

## If anything fails
- Fall back to the saved pytest output and Locust CSVs.
- Do not claim benchmark numbers that are not in the saved run artifacts.
- Do not use real student records or credentials.
