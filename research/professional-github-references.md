# Professional GitHub References for the SIS Project

Research date: 2026-10-19. These are reference candidates, not blanket endorsements. A repository's README and star count do not prove production readiness; inspect code, tests, releases, license, issue activity, dependency health, and security posture before reuse.

## How to use this file

- **Study as domain prior art:** learn how a real SIS models academic entities and workflows.
- **Borrow proven infrastructure patterns:** prefer maintained framework/library examples for rate limiting, IDs, observability, and load testing.
- **Use small enrollment APIs as teaching references:** useful for endpoint boundaries and test structure, but not assumed production-safe.
- **Do not copy an entire ERP into this assignment:** it would bury the system-design experiment under a large product and its dependencies.
## Tier A — authoritative or mature references

### 1. OpenEduCat Community Edition
- Repository: https://github.com/openeducat/openeducat_erp
- License reported by repository: LGPL-3.0.
- Why inspect it: mature education-ERP domain breadth—student records, courses/batches, exams, attendance, timetables, administration.
- Best use: domain vocabulary, entity relationships, module boundaries, and examples of what an SIS commonly already does.
- Not recommended as our project base: Odoo ecosystem and breadth are far larger than this lab needs; it would make our own scaling experiments harder to isolate.
- Research status: repository README and module listing inspected; not a full code/security audit.
### 2. RosarioSIS
- Repository: https://github.com/francoisjacquet/rosariosis
- License reported by repository: GPL-2.0 or later.
- Why inspect it: established open-source SIS with long-lived academic/admin workflows and extensible modules.
- Best use: domain prior art, user roles, reporting, attendance/grades, audit/security considerations.
- Not recommended as our base: PHP and its mature product structure are a different stack; reuse/copying would require careful GPL compliance and may be unnecessary.
- Research status: README, license and repository metadata inspected; not a full code audit.
### 3. OpenTelemetry Demo
- Repository: https://github.com/open-telemetry/opentelemetry-demo
- Overview: https://opentelemetry.io/ecosystem/demo/
- Why inspect it: a living reference for service instrumentation, traces/metrics/logs, collector configuration, dashboards and end-to-end observability.
- Best use: learn how to connect request-level timings to database/service behavior; select only the observability pieces needed for our demo.
- Caution: it is a deliberately broad microservice demo, not a template for our SIS topology. Its own documentation describes it as a living reference implementation.
### 4. Netflix concurrency-limits
- Repository: https://github.com/Netflix/concurrency-limits
- Why inspect it: production-oriented algorithms and rationale for limiting in-flight work based on latency/congestion, not merely requests-per-second.
- Best use: understand overload control and why queue growth can hurt latency; implement a simpler token-bucket or bounded-concurrency mechanism first, then compare.
- Caution: Java library; do not introduce it just to claim an advanced limiter. A small Python implementation is easier to instrument in our stack.
## Tier B — small course-enrollment references

### 5. Enrolli Academic Enrollment System
- Repository: https://github.com/MiladTehrany/academic-enrollment-system
- Stack shown: Java 21, Spring Boot 4, Spring Data JPA, H2, OpenAPI, validation; README describes service and controller tests.
- Useful patterns: Student / Course / CourseOffering / Enrollment separation; unique enrollment constraint; explicit 400/404/409 errors; DTOs; global exception handling; service vs controller tests; Postman collection.
- Critical caveat: repository page showed 0 stars, 2 commits, H2 in-memory, and explicitly lists authentication, rate limiting and pagination as future work. Treat it as a clean small learning reference, not proof of production readiness.
- Link: https://github.com/MiladTehrany/academic-enrollment-system
### 6. Course Enrollment Management System (Java/Spring Boot)
- Repository: https://github.com/bhanuprakash0017/course-enrollment-system
- Stack described: Java 21, Spring Boot 3, PostgreSQL, REST API.
- Useful patterns: inspect API/domain structure and compare its relational model with Enrolli.
- Caveat: search result showed a small repository history (5 commits, 0 stars at time checked); use as a secondary example only, not as a trusted architectural authority.
- Link: https://github.com/bhanuprakash0017/course-enrollment-system
### 7. University Course Registration System
- Repository: https://github.com/Kanan-peoiks/University_Course_Registration
- Stack described: Spring Boot + PostgreSQL + JPA, JavaScript frontend.
- Useful patterns: simple full-stack course registration and relational relationships.
- Caveat: inspect tests, license, capacity enforcement, authorization and concurrency behavior before using any implementation.
- Link: https://github.com/Kanan-peoiks/University_Course_Registration
### 8. Django Student Management System (Django + DevOps)
- Repository: https://github.com/Srivenkatesh03/Student_Management_System
- Stack described: Django/PostgreSQL, Docker Compose, Kubernetes manifests, CI workflows, tests, attendance and marks.
- Useful patterns: environment-based configuration, containerization, CI/test organization, report exports.
- Caveat: a Kubernetes directory does not prove scalability or production readiness; don't adopt Kubernetes for this lab unless it is needed to demonstrate a measured hypothesis.
- Link: https://github.com/Srivenkatesh03/Student_Management_System
### 9. StudentHub / Student Management System
- Repository: https://github.com/tasmiul/student-management-system-django
- Stack described: Django, role-based academic workflows, audit logging, gradebook, attendance, course registration.
- Useful patterns: feature checklist and role-based workflow ideas.
- Caveat: repository is described as active development; validate code, tests, defaults, and license before reuse.
- Link: https://github.com/tasmiul/student-management-system-django
## Tier C — focused infrastructure references

### 10. Locust load testing
- Repository/docs: https://github.com/locustio/locust and https://docs.locust.io/
- Use: model separate student journeys (browse, search, enroll, timetable); generate controlled concurrent load and export latency/throughput/error results.
- Recommendation: use Locust rather than writing a custom load generator. Keep test scripts in our repository so workloads are reproducible.
### 11. Consistent hashing library reference
- Repository: https://github.com/buraksezer/consistent
- Background paper: https://research.google/pubs/consistent-hashing-with-bounded-loads/
- Use: inspect ring/partition abstractions and bounded-load concepts.
- Recommendation: implement a small, transparent Python ring for the assignment first so we can show key placement, node addition/removal and moved-key fraction. Compare with modulo hashing under the same synthetic key set.
- Important: consistent hashing selects a node; it does not by itself migrate data, replicate it, or guarantee failover.
### 12. Sonyflake / KSUID for ID design
- Sonyflake: https://github.com/sony/sonyflake
- KSUID: https://github.com/segmentio/ksuid
- Use: compare distributed/time-sortable ID formats and their assumptions.
- Recommendation: for the first prototype, use database-generated IDs or UUIDv7/ULID from a maintained library unless the assignment specifically needs a custom generator. If we implement a generator, document worker identity, clock behavior, restart safety and collision testing.
### 13. Redis examples
- Redis rate-limiter guidance: https://redis.io/docs/latest/develop/use-cases/rate-limiter/
- Redis cache-aside guidance: https://redis.io/docs/latest/develop/use-cases/cache-aside/
- Use: rate limit and cache selected read-heavy endpoints.
- Recommendation: use Redis as an optional measured layer, not as the authoritative store for enrollment capacity or grades. Add cache invalidation/freshness tests.
## Preliminary recommendation

Use **FastAPI + PostgreSQL + Redis + a small React UI + Locust** as the likely low-friction route, subject to checking the team's preferred stack and environment. This aligns with the user's existing FastAPI/React experience and makes component-level instrumentation accessible.

- PostgreSQL: authoritative records, constraints, transactions and the initial single-database baseline.
- FastAPI: modular monolith for student/course/enrollment/attendance/grades APIs.
- Redis: cache-aside and rate-limiting experiments only after a working baseline exists.
- Python shard router/ring: explicit educational simulation first; only call it real sharding if data is physically separated and routing/migration are demonstrated.
- Locust: repeatable workloads and latency/throughput/error measurements.
- OpenTelemetry or Prometheus metrics: start with a few explicit metrics; do not deploy a large observability stack before it is useful.
- Frontend: prioritize the enrollment contention demo and architecture/metrics dashboard over broad admin CRUD polish.

This is a recommendation, not a locked decision. Validate with a tiny vertical slice and compare effort before expanding.
