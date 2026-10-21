# Feature Backlog

## P0: required
- Registration and authentication, including role checks.
- Student profile management.
- Course catalogue and search.
- Course registration with atomic capacity enforcement and duplicate prevention.
- Attendance entry and summaries.
- Examination and grade management with authorization.
- Timetable access and conflict checks.
- Academic notifications.
- Sharded academic records and consistent-hashing demonstration.
- Three workload levels, metrics, baseline where useful, and a failure/scaling test.

## P1: high-value
- Waitlist with reason codes and explicit policy.
- Prerequisite and credit-limit validation.
- Timetable conflict checker.
- Idempotent registration requests.
- Grade/attendance audit history.
- Retryable in-app notifications.
- Course autocomplete.
- Cache-aside with invalidation.
- Admin dashboard for request, cache and shard metrics.

## P2: optional
- URL shortener for public course resources.
- Crawler for simulated scholarship, internship and course-resource listings.

## Recommended scope
Implement P0 and select a few P1/P2 features that demonstrate the assigned components. Prefer waitlist, conflict checks, audit history, cache-aside, autocomplete and a simulated crawler.

## Avoid overengineering
Do not create eight microservices solely because eight components are listed. Do not add infrastructure without measurable need. Do not call logical tables in one database independent database shards. Never cache authoritative academic writes.