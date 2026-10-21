# Code-Level Review: Enrollment References

Review date: 2026-10-19. Scope is public repository metadata and README-visible design, not a complete clone/build/security audit. Where implementation source was not directly inspectable in this pass, findings are explicitly marked as unverified.

## Executive decision

Use small student enrollment repositories to learn endpoint and DTO structure, not as proof of concurrency correctness. Use mature SIS projects to learn domain vocabulary and edge cases. For the central seat-capacity invariant, implement and test our own PostgreSQL transaction path and compare it against a deliberately unsafe baseline.

Primary references:
- Enrolli: https://github.com/MiladTehrany/academic-enrollment-system
- OpenEduCat: https://github.com/openeducat/openeducat_erp
- RosarioSIS: https://github.com/francoisjacquet/rosariosis
- Multi-service Spring reference: https://github.com/Yousry-Abdelrazek/Course_Management_System
## Reference A — Enrolli (small enrollment REST API)

README-visible strengths:
- Domain model distinguishes Course from CourseOffering (a course scheduled for a professor and term).
- Enrollment has a status, and uniqueness is specified for (student, offering).
- Controller, service, repository, entity and DTO responsibilities are separated.
- Validation and not-found/conflict responses are described; errors use Problem Details.
- README describes service unit tests and controller integration tests.

Limitations visible from its README/repository page:
- Persistence is H2 in-memory; not an adequate substitute for our PostgreSQL concurrency experiments.
- Repository page showed 2 commits and no stars at the time checked; popularity is not the point, but this limits evidence of long-term review.
- README lists authentication, pagination and rate limiting as future work.
- README does not establish that seat capacity is enforced atomically under concurrent requests. Do not assume that it is.

Verdict: best as a small reference for resource naming, DTOs, error responses and test organization. Do not copy its capacity logic unless source inspection and a concurrent integration test prove it correct.
## Reference B — OpenEduCat

README describes a broad education ERP covering admissions/registration, student information, course/batch management, examinations, attendance and timetables.

What we should learn:
- Academic records have more relationships and lifecycle states than a basic Student-to-Course many-to-many.
- Separate a course catalogue item from a term-specific offering.
- Inspect how attendance, exams, scheduling and administration relate before deciding our minimal model.
- Treat mature-product breadth as prior art; don't try to recreate the entire product.

What we should not infer:
- A broad feature list does not prove our desired architecture or its performance.
- We have not completed a code-level audit of OpenEduCat's concurrency, authorization or deployment behavior.

Verdict: domain discovery and feature-gap reference, not our codebase.
## Reference C — RosarioSIS

README/help/change-history pages show real school workflows such as scheduling, attendance, grade reporting, enrollment/drop lifecycle, and restrictions against duplicate course-period enrollment. Its history includes fixes around enrollment, attendance and access control.

What we should learn:
- Dropping a student/course is a lifecycle transition, not necessarily deletion of the historical record.
- Academic changes may affect grades, attendance, credits and reports; deletion can have cascading consequences.
- Schedule conflict detection and course restrictions are real domain concerns.
- Long-lived systems evolve through fixes; our report should acknowledge edge cases and regression tests.

Limitations:
- It is a school-oriented PHP application, so it is not a direct architecture template for our proposed FastAPI/PostgreSQL stack.
- A changelog demonstrates real maintenance concerns, not that every current code path is correct.

Verdict: lifecycle and domain edge-case reference.
## Reference D — Multi-service Spring course-management example

Repository: https://github.com/Yousry-Abdelrazek/Course_Management_System

README describes separate admin and public services, shared core code, role-gated APIs, JWT-related security tests, and tests for registration-window validation.

Useful:
- Test role access at API boundaries.
- Test registration windows as business rules.
- Shared DTO/entity code can reduce duplication, but can also create coupling.

Why not copy the topology:
- Multiple services introduce network calls, duplicated configuration, service-specific persistence/access rules and distributed failure modes.
- Our lab already needs to demonstrate several system-design components; a modular monolith is easier to instrument and reason about.
- We should only split a service if a workload or failure test demonstrates a reason.

Verdict: selective reference for security/test cases, not an initial architecture.
## The most important implementation gap: seat capacity

A typical unsafe implementation does this:
1. Read current enrollment count.
2. If count is below capacity, continue.
3. Insert enrollment.

Two concurrent transactions can both read the same remaining seat and both insert. A rate limiter can reduce pressure but cannot establish correctness.

Our acceptance invariant:
- For every offering: active enrolled count must never exceed capacity.
- For each student/offering pair: at most one active enrollment.
- A failed enrollment must not consume a seat.
- Retrying the same logical request must not create duplicate enrollments.
## Recommended PostgreSQL transaction pattern

Keep the database as the authority. One simple design is to maintain enrolled_count on the offering row and perform a conditional atomic update within the same transaction as the enrollment insert:

    UPDATE course_offerings
    SET enrolled_count = enrolled_count + 1
    WHERE id = :offering_id
      AND status = 'OPEN'
      AND enrolled_count < capacity
    RETURNING id;

If no row is returned, the offering is closed or full. If the update succeeds, insert the enrollment in the same transaction. Any insert/constraint failure must roll back the counter update too.

Also enforce a database unique constraint on (student_id, offering_id) for active registration semantics. If the system allows drop then re-enroll, choose a schema/constraint strategy that models history correctly (e.g. separate enrollment attempts/history or a partial unique index for active records). Do not rely only on a prior application-level SELECT.
## Alternative and trade-offs

- **Lock the offering row then count active enrollments:** easy to explain; serialize requests for the same offering; count query and lock must be in one transaction, and all enrollment writers must follow the same protocol.
- **Conditional counter update:** efficient seat reservation under contention, but counter correctness must be maintained on drops/cancellations and audited against actual active rows.
- **Serializable isolation:** can protect invariants with retries, but introduces serialization failures and requires correct retry handling; do not select it just because it sounds stronger.
- **Redis seat counter:** not authoritative for this assignment's correctness baseline. It creates a dual-write/consistency problem unless backed by a carefully designed protocol.

For a student lab, start with a transaction + row lock or conditional update; compare correctness and throughput under synchronized contention.
## Test plan derived from the review

1. Capacity boundary: capacity 5, 20 concurrent distinct students; exactly 5 succeed.
2. Duplicate request: same student submits concurrently many times; only one active enrollment.
3. Rollback: force enrollment insert failure after seat increment; counter must remain unchanged.
4. Drop/re-enroll: count decreases once; one re-enrollment succeeds if policy allows it.
5. Closed offering: no new enrollment even when seats remain.
6. Eligibility race: if prerequisites/credit limits apply, revalidate them at commit, not only in preflight UI.
7. Retry: a timeout followed by client retry must return the original outcome or a safe conflict, not create a second enrollment.
8. Multi-process: run multiple API workers against the same PostgreSQL database; in-process mutexes do not count as distributed correctness.

## Sources
- Enrolli repository and README: https://github.com/MiladTehrany/academic-enrollment-system
- OpenEduCat repository: https://github.com/openeducat/openeducat_erp
- RosarioSIS README/help/change history: https://github.com/francoisjacquet/rosariosis
- Multi-service Spring example: https://github.com/Yousry-Abdelrazek/Course_Management_System
- PostgreSQL transaction isolation: https://www.postgresql.org/docs/current/transaction-iso.html
- PostgreSQL explicit locking: https://www.postgresql.org/docs/current/explicit-locking.html

## Source inspection: Enrolli enrollment service (repository cloned locally)

I cloned the repository to /home/sujith/Documents/SIS-Karpathy-Map/references/enrolli and inspected EnrollmentServiceImpl.java, EnrollmentRepository.java, CourseOffering.java, Enrollment.java, and EnrollmentServiceImplTest.java. This is a source-level review of the current shallow clone, not a full execution/security audit.

### Confirmed useful patterns
- Enrollment creation is marked @Transactional.
- CourseOffering is a separate entity with course, professor, term, capacity and status.
- Enrollment has a database unique constraint on student_id + offering_id.
- Service tests cover open/closed offering, duplicate request, full capacity and missing resources.
- A fetch-join query is used for the student's term enrollment listing, which can avoid repeated lazy-load queries for those relations.

### Confirmed correctness gaps in the inspected implementation
1. **Seat-capacity race:** service performs COUNT(ENROLLED), compares it with capacity, then inserts. No row lock, atomic conditional update, or serializable retry is visible in this path. Two concurrent transactions may both observe the same last seat and both pass the count check. @Transactional alone does not prevent this under typical READ COMMITTED isolation.
2. **Duplicate check is not enough:** the service first calls existsByStudentIdAndCourseOfferingId, then inserts. Concurrent duplicate requests can both pass that check; the unique constraint is the final guard, but the service should translate the constraint violation into a stable 409 response.
3. **Drop/re-enroll lifecycle conflict:** Enrollment has a DROPPED status and a drop() method, but the table's unique constraint is on the student/offering pair regardless of status. If a dropped row is retained, inserting a new row for the same student/offering is blocked. The domain must explicitly choose whether reactivation is supported or history is modelled separately.
4. **Unit tests do not prove concurrency correctness:** the inspected service tests mock repository methods and assert single-call behavior. They don't run concurrent transactions against a real database, so they cannot expose the capacity race.

These are not reasons to dismiss the repository: it is a useful compact example precisely because its clean structure makes the missing concurrency guarantees easy to identify. We should not copy its capacity path unchanged.
