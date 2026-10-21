# Engineering Roadmap: SIS

## Mission
Build a correctness-first Student Information System that survives registration bursts and proves its claims with repeatable experiments. This is a lab prototype, not a claim of production readiness.

## Engineering method: Question → Delete → Simplify → Accelerate → Automate
Inspired by Elon Musk's publicly described five-step engineering algorithm; used here as a review heuristic, not a universal law.
1. **Question:** every requirement must map to a user problem, assignment criterion, owner/source, and acceptance test.
2. **Delete:** reject decorative features and infrastructure without a testable purpose.
3. **Simplify:** start as a modular monolith with PostgreSQL; add Redis/shards only when the experiment needs them.
4. **Accelerate:** shorten build-test-measure cycles; run small reproducible experiments before large load tests.
5. **Automate:** only automate stable tests, repeatable load profiles, metrics collection, and report generation.

## Build sequence
- **Phase 0 — evidence & scope:** validate problem stories; separate assignment-mandated components from optional features.
- **Phase 1 — domain correctness:** schema, roles, course offerings, seat capacity, prerequisites, timetable conflicts, idempotent enrollment.
- **Phase 2 — usable vertical slice:** student search → offering details → enroll/drop → outcome and audit trail.
- **Phase 3 — baseline:** synthetic dataset, seeded known cases, unit/integration tests, single DB and no cache.
- **Phase 4 — scale components:** rate limiting, cache-aside, shard router, consistent-hash routing and unique IDs, one at a time.
- **Phase 5 — measured failure:** synchronized last-seat race, retries, overload, cache outage, app-node removal, shard membership change.
- **Phase 6 — presentation:** measured graphs, architecture, limitations, reproducible demo, poster and report.

## Definition of done
- Capacity invariant holds under concurrency; duplicate enrollment is impossible.
- Retries return the same logical result via idempotency key.
- Students cannot read other students' private records; role checks are server-side.
- Baseline and each optimization use the same dataset/request mix.
- Results include p50/p95 latency, throughput, error rate, resource use and correctness violations.
- Every claim is backed by a test or labelled as a design intention.

## Explicit non-goals
No premature microservices/Kubernetes, no AI chatbot just for novelty, no real student data, no invented benchmark results, and no claim that consistent hashing alone migrates data or provides failover.