# Architecture Principles

## Recommended shape
Start with a modular monolith plus explicit supporting components. This is easier to develop and demonstrate than eight microservices.

UI (student/faculty/admin) → API/authentication → rate limiting/validation → academic modules (profiles, courses, registration, attendance, grades, timetable) → shard router → Shard A/B/C.

Supporting modules: autocomplete, unique IDs, notifications, optional crawler and URL shortener. A key-value cache serves selected read-heavy paths.

## Data ownership
- Student profile: authoritative student record.
- Course offerings: authoritative catalog and capacity.
- Enrollment: authoritative registration record.
- Attendance: session-level records.
- Grades: authoritative grade plus audit history.
- Notifications: persisted delivery state.
- Cache: disposable read copy.
- Crawler output: separate resource records with source and fetch time.

## Integrity rules
Use unique constraints, transactions for seat allocation, role/object authorization, idempotent writes and audit history.

## Sharding decisions to document
1. Sharded entities and partition keys.
2. Routing algorithm.
3. Cross-shard query handling.
4. Add/remove shard and migration strategy.
5. Verification for missing/duplicate records.
6. Behaviour when a shard is unavailable.

If enrollment is sharded by student, course capacity still needs course-oriented coordination. Do not ignore cross-shard atomicity.

## Failure behaviour
- DB write fails: do not report success.
- Client times out after commit: idempotency prevents duplicate effects.
- Cache fails: bypass only if database capacity allows.
- App server fails: health-aware routing is needed for automatic avoidance.
- Shard fails: fail affected writes safely unless real replication exists.
- Notification fails: retain retryable state.
- Crawler source fails: preserve prior data and mark it stale.