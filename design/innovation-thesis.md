# Innovation Thesis: What Makes This SIS More Than CRUD?

## User problem
During registration peaks, students need a trustworthy answer: did I get the seat, am I waitlisted, or was I rejected—and can I retry safely? Staff need accurate capacity and auditable grade/attendance changes. A fast but incorrect portal is a failure.

## Proposed differentiators
- **Seat-integrity lab:** synchronized competition for the final seats, with a visible invariant counter. Show that successful enrollment never exceeds capacity.
- **Retry-safe enrollment:** client supplies an idempotency key; retrying after timeout does not create a second enrollment or consume another seat.
- **Explainable outcomes:** structured results such as ENROLLED, WAITLISTED, FULL, PREREQUISITE_FAILED, TIMETABLE_CONFLICT, RATE_LIMITED; include next action and retry guidance.
- **Fair overload behavior:** per-user rate limits plus bounded concurrency/queue policy; publish accepted/rejected counts. Rate limiting is not the seat-capacity lock.
- **Honest scalability explorer:** compare single DB vs logical shards, modulo vs consistent hashing, cache off/on, and node add/remove. Show p95 latency, load skew and key movement, while clearly stating migration/failover limits.
- **Freshness-aware read path:** cache public course catalogue/timetable data with TTL and invalidation tests; never use a stale cache as the authority for seat availability.
- **Auditability:** append-only history for grade/attendance changes with actor, time and reason; no sensitive data in logs.
- **Accessible search:** course autocomplete supports course code, title, instructor and department, with bounded results and measured top-k relevance.

## Innovation discipline
The individual techniques are established engineering patterns. Our innovation is their integrated, tested demonstration against a real workflow and a clear comparison of correctness, fairness, latency and failure behavior—not claiming to invent distributed systems.

## Priority
**Must build:** atomic enrollment, idempotency, roles, course search, attendance/grades, audit trail, synthetic load test and component metrics.
**Build if time permits:** waitlist promotion, cache freshness, autocomplete, live experiment dashboard.
**Optional/assignment-driven:** crawler and URL shortener; implement only if their required component mapping is explicitly assessed.
**Do not build:** AI advisor/chatbot, complex microservices, Kubernetes, or elaborate UI before core invariants pass.

## Success statement
“Under a documented synthetic workload, the system preserves seat capacity and duplicate-prevention invariants, reports useful outcomes under overload, and quantifies the performance and trade-offs of each scaling component.”