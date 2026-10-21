<div align="center">

# Orbit SIS

**A Student Information System that only claims what it measured.**

A working academic system — registration, enrollment, grades, attendance, timetables — rebuilt so that
every architectural claim in it is backed by a test, a benchmark, or an explicit statement of its limits.

<sub>UCS3513 System Design Laboratory · coursework prototype · SSN College of Engineering</sub>

![Python 3.12](https://img.shields.io/badge/Python-3.12-2fb8a0?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.148-2fb8a0?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17-2fb8a0?style=flat-square&logo=postgresql&logoColor=white)
![React 19](https://img.shields.io/badge/React-19-2fb8a0?style=flat-square&logo=react&logoColor=white)
![Tests](https://img.shields.io/badge/tests-24-2fb8a0?style=flat-square)
![Status](https://img.shields.io/badge/status-coursework%20prototype-ff5a4f?style=flat-square)

<img src="deliverables/screenshots/00-overview-viewport.png" alt="Orbit SIS dashboard" width="820">

</div>

---

## What this is

A complete, runnable Student Information System: student registration and signed bearer tokens, a course
catalogue and term offerings, transaction-safe enrollment with seat capacity and idempotency keys,
attendance, assessments and grades, timetable events, notifications, and a staff workspace — served by a
FastAPI modular monolith against PostgreSQL, with a React 19 single-page frontend.

On top of that workflow it implements **eight system-design components** required by the assignment as
explicit, observable experiments: rate limiting, sharding, consistent hashing, a key-value cache, a
time-sortable ID generator, a URL shortener, a bounded web crawler, and autocomplete.

The distinguishing idea is not the feature list. It is **how the claims are made.**

## The thesis

> An SIS is a correctness-sensitive system under bursty load. So the interesting question is never
> "does enrollment work?" — it is "what exactly makes it correct when twenty students race for five seats?"

The prototype's answer: **a preflight read is not a correctness boundary.** The transaction below is:

```mermaid
sequenceDiagram
    participant R as Concurrent requests
    participant DB as PostgreSQL
    R->>DB: Authenticated, idempotency-key checked
    R->>DB: UPDATE offering SET enrolled_count = enrolled_count + 1<br/>WHERE id = :id AND status = 'OPEN' AND enrolled_count below capacity
    Note over DB: The conditional update is the gate.<br/>A lost race updates zero rows and returns HTTP 409.
    R->>DB: INSERT enrollment (same transaction)
    Note over DB: Partial unique index allows exactly<br/>one ACTIVE enrollment per student/offering.
    DB-->>R: COMMIT both, or roll back the seat increment
```

That path is not asserted in prose — it is executed. A verification suite runs **20 distinct students
concurrently requesting 5 seats** and asserts that exactly 5 requests succeed, 15 return HTTP 409, and
that both the stored `enrolled_count` and the active enrollment rows equal 5. A duplicate-enrollment race
test asserts that concurrent requests for the same student leave exactly one active row and one counter
increment.

## Architecture

<div align="center">
<img src="deliverables/diagrams/architecture.svg" alt="System architecture" width="700">
</div>

PostgreSQL is authoritative for students, courses, offerings, enrollments, grades, attendance, timetable
entries, notifications, and short links. The cache is an optimization only — it is never consulted to
decide whether a seat is available or a grade is valid. The rate limiter, cache, hash ring and shard
store are deliberately **process-local lab components**, and the documentation says so rather than
dressing them up as a distributed system.

## Required system-design components

Each component is implemented as a measurable experiment, with its limitation stated up front.

| Component | Implementation | How it is demonstrated | Stated limitation |
|---|---|---|---|
| Rate limiter | Thread-safe token bucket in HTTP middleware | HTTP 429 counts, request/error metrics | Process-local; not shared across replicas |
| Sharding | Synthetic records in per-shard dictionaries | Record count per shard, orphaned keys | Not PostgreSQL data sharding |
| Consistent hashing | SHA-256 ring, 100 virtual nodes per shard | Add-node experiment reports moved-key fraction | Routing does not migrate or replicate data |
| Key-value store | Bounded TTL + LRU cache for autocomplete | Hits, misses, item count, latency delta | Process-local; up to 20 s stale |
| Unique ID generator | Time-sortable 64-bit ID + worker ID + sequence | Batch size, uniqueness in batch, collisions | Worker ID fixed; no multi-worker coordination |
| URL shortener | Random short code persisted in PostgreSQL | Create/redirect latency under load | No expiry, analytics or abuse policy yet |
| Web crawler | Bounded same-host public-HTTPS crawler | Pages crawled, failures, frontier size, elapsed | Not a general-purpose distributed crawler |
| Autocomplete | Course-code/title prefix query + TTL cache | p50/p95 and cache hit/miss counts | Prefix only; no typo tolerance or ranking |

## Measured results

10 simulated users, 20-second runs, 1,000 students / 100 courses / 200 offerings on one local machine
(i5-1135G7, 8 logical CPUs), app + database + load generator sharing the host. Response times in ms.

| Workload | Requests | Failures | p50 | Mean | p95 | Throughput |
|---|---:|---:|---:|---:|---:|---:|
| Autocomplete, cache disabled | 659 | 0 | 5 | 5.85 | 10 | 34.68 req/s |
| Autocomplete, cache enabled | 675 | 0 | 2 | 2.88 | 5 | 35.55 req/s |
| Course search + offering list | 681 | 0 | 5 | 5.65 | 10 | 35.82 req/s |
| Authenticated profile / grades / enrollments / timetable | 669 | 0 | 5 | 7.43 | 12 | 35.27 req/s |
| Student registration writes | 370 | 0 | 60 | 63.63 | 83 | 19.47 req/s |
| Course-search overload, rate limiter on | 676 | 243 (35.95%) | 4 | 4.27 | 10 | 35.61 req/s |

**What the numbers support.** With cache enabled, autocomplete mean latency fell ~50.8% (5.85 → 2.88 ms),
p50 fell 60% (5 → 2 ms) and p95 fell 50% (10 → 5 ms) — with essentially unchanged throughput. Registration
writes are deliberately slow (p50 60 ms) because passwords use PBKDF2-HMAC-SHA256 at 310,000 iterations;
that is a security/performance trade-off, not a bug. The overload run returned 243 HTTP 429s: admission
control working, and simultaneously evidence that the offered load exceeded the configured budget.

**What the numbers do not support.** These are local prototype measurements, not a capacity claim.
The application, load generator and database share one machine, so cross-host network latency is absent.
Caching did not improve throughput here and may not generalize. Rejected requests did not succeed — rate
limiting protects the service, it does not create capacity. Every limitation is written down in
[`sis-app/docs/PERFORMANCE_EVALUATION.md`](sis-app/docs/PERFORMANCE_EVALUATION.md) rather than smoothed over.

## Frontend

A React 19 + TypeScript + Vite SPA, served by FastAPI from `dist/`. The visual direction is a
**peak 80s/90s graphic-poster** aesthetic rebuilt from reference imagery: off-white paper `#f4efe3` with
halftone dots, ink `#1c1a18` at 3px borders, hard non-blurred offset shadows, square corners, and a
coral / electric-blue / mustard / lavender / violet / mint poster palette, set in Bungee, Space Grotesk
and VT323.

Contrast and legibility are treated as correctness, not taste: every text pair is explicitly defined for
both light and dark themes, and no text renders below 12 px. That pass is verified by measuring computed
`color` against the effective background for every text node across all seven sections, in both themes —
dark mode reports zero contrast failures.

<div align="center">
<img src="deliverables/screenshots/02-courses-desktop.png" alt="Course catalogue" width="410">
<img src="deliverables/screenshots/03-enrollment-confirmed.png" alt="Confirmed enrollment" width="410">
</div>

More captures, and what each one proves, are indexed in
[`deliverables/screenshots/README.md`](deliverables/screenshots/README.md). All screenshots use synthetic
demonstration data — no real student records.

## Quick start

Requires Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Node 20+, and Podman or a PostgreSQL 17 server.

```bash
git clone https://github.com/sujith0613/sis-system-design.git
cd sis-system-design/sis-app

uv sync --extra test --extra benchmark --extra dev --extra deliverables

# Start PostgreSQL (see docs/DEMO_RUNBOOK.md), then configure .env from .env.example
uv run alembic upgrade head
uv run python -m scripts.generate_dataset --students 1000 --courses 100 --offerings-per-course 2
uv run python -m scripts.create_staff --email staff@example.test --student-number STAFF001
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Build the frontend so FastAPI serves the SPA instead of its fallback page:

```bash
cd frontend && npm ci && npm run build
```

Then open <http://127.0.0.1:8000/> for the dashboard or <http://127.0.0.1:8000/docs> for the API
reference. Register a student in the dashboard; use the staff account from step 5 for catalogue, offering,
attendance, grade, timetable and notification management. Full walkthrough: [`sis-app/docs/DEMO_RUNBOOK.md`](sis-app/docs/DEMO_RUNBOOK.md).

## Tests

```bash
cd sis-app
# Integration tests drop and recreate tables — point them at a dedicated database.
DATABASE_URL='postgresql+psycopg://sis:sis_dev_only@localhost:5432/sis' \
  SIS_RATE_LIMIT_ENABLED=false uv run pytest -q
```

24 tests across authentication and access control, academic workflows, the eight design components, the
crawler, the API surface, and PostgreSQL concurrency. The concurrency tests are the ones that matter:
they are the difference between "we designed for races" and "we ran the race."

## Repository layout

```
sis-app/                 FastAPI app, React frontend, migrations, tests, Locust workloads
  app/                   auth, models, schemas, components, extended routes, crawler
  frontend/              React 19 + TS + Vite SPA (src/retro.css = theme layer)
  docs/                  architecture, component trade-offs, performance, demo runbook
  tests/                 24 tests incl. PostgreSQL concurrency and race suites
  results/               saved Locust CSVs behind the numbers above
research/                problem landscape, institutional evidence, security & privacy, sources
design/                  domain model, architecture decisions, component mapping, innovation thesis
experiments/             evaluation plan and implementation status
deliverables/            system-design report (PDF + LaTeX), poster, presentation, diagrams, screenshots
testing/                 JMeter/Postman assets and verification evidence
scripts/                 report, poster and presentation generators
```

## Documentation

| Document | What it covers |
|---|---|
| [Architecture](sis-app/docs/ARCHITECTURE.md) | Component map, domain model, the enrollment transaction, trust boundaries |
| [Components and trade-offs](sis-app/docs/COMPONENTS_AND_TRADEOFFS.md) | Per-component implementation, measurement and limitation |
| [Performance evaluation](sis-app/docs/PERFORMANCE_EVALUATION.md) | Method, results, interpretation, reproduction steps |
| [Demo runbook](sis-app/docs/DEMO_RUNBOOK.md) | Environment setup and end-to-end walkthrough |
| [System design report](deliverables/system-design-report.md) | The full written submission |
| [Domain model](design/domain-model-v1.md) · [Architecture decisions](design/architecture-decisions.md) | Design rationale |
| [Innovation thesis](design/innovation-thesis.md) · [Evaluation plan](experiments/evaluation-plan.md) | Cross-domain ideas and how they were tested |
| [Frontend design system](design/frontend-design-system.md) | Visual direction and its research basis |

## What this is not

The honest version, because a system-design submission is judged on the quality of its claims:

- **Not a production SIS.** Single-host, single-process, no deployment, no HA, no backups, no ops story.
- **Not a microservices system.** It is a modular monolith, chosen because independent scaling or fault
  isolation would need to be justified by measurement the prototype does not have.
- **Not real sharding.** Shards are synthetic in-memory dictionaries; consistent hashing routes keys and
  never migrates or replicates data.
- **Not a distributed cache or limiter.** Both are process-local and reset on restart.
- **Not a live crawler result.** Crawler behavior is verified against a mocked HTTPS response; DNS was
  unavailable during verification, so no live-crawl throughput is claimed.
- **Not real student data.** Everything is generated synthetically.

## Academic context

Coursework for **UCS3513 System Design Laboratory**, SSN College of Engineering. Published as a private
reference for evaluation and portfolio review. It is not licensed for reuse or resubmission; the
supporting research notes in `research/` cite their sources and separate prior art from this
implementation, including a source-level review of the public Enrolli enrollment service that identified
a count-then-insert capacity race with mock-only unit tests — the specific failure this design avoids.

<div align="center">
<sub>Built by <a href="https://github.com/sujith0613">Sujith M</a> · CSE, SSN</sub>
</div>
