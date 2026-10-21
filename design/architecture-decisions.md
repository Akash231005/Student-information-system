# Architecture Decision Records — SIS

Date: 2026-10-19. These decisions are provisional and should be revisited when an experiment provides contrary evidence.

## ADR-001: Start with a modular monolith
**Decision:** One FastAPI application with modules by domain, one PostgreSQL database initially.

**Why:** The assignment is about system-design mechanisms and their evaluation, not proving that splitting a CRUD application into microservices is possible. A modular monolith reduces network failure modes, deployment work and duplicated configuration while we establish correctness and a benchmark baseline.

**Revisit if:** A required experiment specifically needs independent service scaling/failure, or measured bottlenecks justify extraction.

## ADR-002: PostgreSQL is the source of truth
**Decision:** Store authoritative enrollment, capacity, attendance and grade state in PostgreSQL.

**Why:** Constraints, transactions, row locks and conditional updates provide a clear place to enforce academic invariants. Redis is not the authority for seats or grades.

**Required evidence:** A real-PostgreSQL integration test with concurrent requests. Unit mocks alone are insufficient.
## ADR-003: CourseOffering is distinct from Course
**Decision:** A Course is the catalogue definition; a CourseOffering is a specific section in a term with instructor, capacity, status and registration window.

**Why:** Capacity and availability belong to the offering, not the general catalogue item. This structure is also present in the Enrolli reference.

## ADR-004: Implement idempotency before calling enrollment retry-safe
**Decision:** Enrollment POST accepts an idempotency key (or equivalent request identifier) and persists its outcome under a uniqueness scope.

**Why:** A client can time out after the server commits; retrying must not create a second logical action. A unique enrollment constraint protects duplicate active enrollment but does not fully define retry response semantics.

## ADR-005: Baseline before cache and sharding
**Decision:** First benchmark one PostgreSQL instance with no cache and no sharding. Add one mechanism at a time.

**Why:** Otherwise we cannot attribute changes in latency, throughput, errors or resource use to a specific design choice.
## ADR-006: Treat the eight required components as experiments, not eight services
**Decision:** Map each required component to an explicit workload, module or small subsystem. Do not create one microservice per component by default.

- Rate limiter: protect login/registration/search endpoints.
- Sharding: partition synthetic data only after single-database baseline.
- Consistent hashing: route keys among simulated shards/nodes; measure key movement when nodes change.
- Key-value store: cache selected catalogue/search reads.
- Unique ID generator: implement or integrate after defining collision/restart requirements.
- URL shortener: bounded link redirect feature for public course resources.
- Web crawler: restricted, synthetic or allow-listed course resource indexer.
- Autocomplete: course code/title prefix search with latency and top-k evaluation.
## ADR-007: Keep academic preflight advisory, then revalidate at commit
**Decision:** A preview can tell a student about prerequisite, timetable, credit-limit or capacity issues. The enrollment transaction must revalidate rules that can change before commit.

**Why:** A preflight screen is not a seat reservation; state may change between preview and submission.

## ADR-008: Measure fairness and correctness, not just speed
**Decision:** Report p50/p95 latency, throughput, error rate, resource use and invariant violations. For enrollment, correctness violations must be zero in every accepted run.

**Why:** A system that accepts too many students faster is not a successful optimization.
