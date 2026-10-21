# 10-Minute Presentation Outline

## Slide 1 — Problem and requirements (45 s)
Scalable SIS: profiles, course discovery/registration, attendance, exams/grades, timetable, notifications. The main correctness risk is concurrent registration for a limited number of seats.

## Slide 2 — Engineering thesis (45 s)
Correctness before scale; measure before distributing. The key contribution is an explainable correctness-first design plus repeatable experiments, not an inflated list of technologies.

## Slide 3 — Architecture and domain model (75 s)
FastAPI modular monolith; PostgreSQL source of truth; separate Course and CourseOffering; Enrollment transaction; lightweight dashboard; Locust workloads.

## Slide 4 — Critical path: seat reservation (90 s)
Conditional atomic update + transaction + unique constraints + idempotency key. Show why a separate COUNT-then-INSERT can oversell. Present the capacity=5, 20-concurrent-request test.

## Slide 5 — Academic workflows and validation (60 s)
Auth demo, profile, attendance uniqueness, marks bounds, timetable room conflict, notifications, drop releasing one seat exactly once.

## Slide 6 — Eight required system-design components (90 s)
Rate limiter (Redis-backed), sharding (real two-shard MongoDB cluster), consistent hashing, Redis TTL key-value cache, unique IDs, URL shortener, bounded crawler, autocomplete. Explain one metric and one limitation per component.

## Slide 7 — Workloads and results (90 s)
Separate course search, profile reads, student writes and autocomplete runs. Report users, duration, throughput, p50/p95, errors and dataset. Distinguish smoke tests from repeatable baseline runs.

## Slide 8 — Failure modes and trade-offs (60 s)
Process-local versus shared state, ring changes do not migrate data, cache can be stale, database remains authoritative. Staff mutations and student self-record reads have role/scope checks, but token revocation and production identity controls are absent.

## Slide 9 — Innovation and conclusion (45 s)
Academic Safety Case: the system explains the transactional constraints behind enrollment decisions and demonstrates the invariant under concurrent load. Next: token revocation/refresh, Redis shared limiter/cache, shard migration, crawler hardening and larger repeated benchmarks.
