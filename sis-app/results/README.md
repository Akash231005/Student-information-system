# Performance results

## Current post-RBAC runs

- final-course-search-rerun: valid course discovery baseline; the earlier final-course-search run had transient 500 responses while tables were being recreated and has been archived.
- final-profile-reads: authenticated profile/enrollment/grade reads; its stats include per-user auth setup requests, so use individual endpoint rows for read-only latency.
- final-student-registration: password-hashed account-registration write workload.
- final-autocomplete: cache-enabled autocomplete workload.
- final-autocomplete-cache-off: matched cache-disabled autocomplete workload against the same synthetic dataset.
- final-rate-limiter-on: current 12-second, 10-user course-discovery run with the token bucket enabled; 83/401 requests received HTTP 429.

The four baseline workload runs used 10 users, a 2 users/s spawn rate and an 8-second duration with rate limiting disabled. The separate final-rate-limiter-on run used 10 users for 12 seconds with the token bucket enabled. All are short single runs, useful for coursework comparison only.

## Archived runs

The archive folder contains earlier pre-RBAC runs and the initial smoke test. Some are not comparable to the current API contract. The initial course-search run also captured two transient 500s during database-table recreation; use the rerun for the current baseline.

For each new comparison, record commit/version, machine, database config, data size, workload mix, users, spawn rate, duration, p50/p95/p99, throughput, failure rate, CPU/memory, DB connections and invariant checks. Never compare runs from different workload mixes as if they were controlled experiments.
