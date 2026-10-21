# GitHub Reference Projects and Patterns

Research snapshot: 2026-10-19. These are reference implementations/patterns, not a claim that every repository is trending. Inspect activity, issues, license and code before adopting anything.

## Strong engineering references
- [Locust](https://github.com/locustio/locust) — Python load-test scenarios, live latency/throughput/error charts, exportable results. Borrow: reproducible workload profiles.
- [OpenTelemetry Demo](https://github.com/open-telemetry/opentelemetry-demo) — realistic distributed app with observability. Borrow: trace/metric thinking; do not copy its microservice count.
- [buraksezer/consistent](https://github.com/buraksezer/consistent) — Go consistent hashing with bounded loads and partitions. Borrow: compare distribution and key movement; adapt concepts, not necessarily language.
- [Netflix/concurrency-limits](https://github.com/Netflix/concurrency-limits) — concurrency-based admission control inspired by congestion control. Borrow: demonstrate why request-rate limits and concurrency limits differ.
- [redis/fastapi-redis-sdk](https://github.com/redis/fastapi-redis-sdk) — FastAPI cache/rate-limit/session integration. Borrow: shared limiter state across workers, cache lifecycle and metrics.
- [segmentio/ksuid](https://github.com/segmentio/ksuid) — time-sortable globally unique IDs. Borrow: compare UUID/DB IDs/custom generator only if required by assignment.
- [sony/sonyflake](https://github.com/sony/sonyflake) — distributed ID generation with explicit time/machine/sequence trade-offs.
- [pgvector/pgvector](https://github.com/pgvector/pgvector) — vector search inside PostgreSQL. Not needed unless semantic course/resource search is a demonstrated requirement.

## Domain examples to inspect critically
- [MiladTehrany/academic-enrollment-system](https://github.com/MiladTehrany/academic-enrollment-system) — course offerings, enrollment and capacity domain model.
- [1R-Vinay/Course_Registration](https://github.com/1R-Vinay/Course_Registration) — full-stack course registration with full-section and schedule-conflict handling described in README.
- [Akash1362000/Django_Student_Management_System](https://github.com/Akash1362000/Django_Student_Management_System) — student dashboard, attendance, feedback and results.
- [jobic10/student-management-using-django](https://github.com/jobic10/student-management-using-django) — role-specific student/staff/admin workflows.
- [nikhilken14/fastapi-rate-limiting](https://github.com/nikhilken14/fastapi-rate-limiting) — Redis Lua token bucket and cross-instance demonstration.

## What to learn, not copy
1. Domain repositories help identify expected workflows; they do not prove scalable architecture or correctness under contention.
2. Load-testing and observability repos are more valuable to our differentiator than a feature-rich CRUD clone.
3. Reproduce a tiny core pattern and write tests around its invariant; avoid importing an entire stack.
4. Check latest commit, release cadence, issues, tests and license at adoption time. Stars are popularity signals, not quality guarantees.