# SIS Domain Model — Version 1

Status: proposed design for the first vertical slice, informed by the assignment and source review of public SIS/enrollment repositories. This is not yet final implementation.

## Design goals
- Model a term-specific course offering separately from the course catalogue.
- Keep academic records relational and transactional.
- Make registration rules explicit and testable.
- Preserve history when a student drops a course.
- Keep the first implementation small enough to benchmark before adding complexity.

## Core entities

### Student
- id: internal primary key
- student_number: unique institutional identifier
- full_name
- email: unique if policy requires it
- department / programme
- created_at, updated_at
- status: active / inactive

### Course
- id
- course_code: unique
- title
- credits
- description
- status: active / retired

### CourseOffering
- id
- course_id -> Course
- instructor_id -> Instructor
- term_code (e.g. 2026-FALL)
- section_code
- capacity
- enrolled_count (optional maintained counter; if used, audited against active enrollments)
- registration_open_at, registration_close_at
- status: draft / open / closed / cancelled
- unique offering identity: course + term + section (and instructor only if the institutional rule requires it)
### Enrollment
- id
- student_id -> Student
- offering_id -> CourseOffering
- status: enrolled / dropped / waitlisted
- created_at, dropped_at
- request_id / idempotency key reference for retry safety
- policy outcome code and policy version where useful for explainability

The final uniqueness strategy must support the chosen drop/re-enroll rule. A single permanent unique constraint on student_id + offering_id blocks a new row after drop; deleting old rows loses history. Preferred starting option: keep one enrollment record per student/offering and transition its status back to ENROLLED only if reactivation is allowed, with a separate audit event for each transition. If the product needs multiple attempts/history rows, use an enrollment_history/event table and a database-enforced active-row uniqueness strategy.

### AttendanceRecord
- id
- student_id, offering_id, session_date
- status: present / absent / late / excused
- recorded_by, recorded_at, updated_at
- unique student + offering + session_date

### Assessment / Grade
- Assessment: id, offering_id, name, max_score, due_date
- Grade: id, assessment_id, student_id, score, published_at, updated_at, updated_by
- validate score bounds; enforce faculty authorization; audit edits and publication.

### AuditEvent
- id, actor_id, action, entity_type, entity_id
- occurred_at, request_id, outcome_code
- minimal before/after metadata where appropriate; never store passwords/tokens or unnecessary sensitive data
## Supporting entities for later phases

### IdempotencyRecord
- key, actor_id, route/operation, request_hash, response_status, response_body or result reference, created_at, expires_at
- Unique scope such as actor + operation + key.
- Same key + same request returns the stored outcome; same key + different request is rejected.

### WaitlistEntry (optional)
- id, student_id, offering_id, priority timestamp, status, eligibility snapshot/version
- Only add after basic enrollment correctness is proven.
- If a seat opens, revalidate all eligibility and timetable rules at promotion time.

### NotificationOutbox (optional)
- id, event_type, payload reference, status, attempts, next_attempt_at, created_at
- Write outbox event in the same transaction as the academic state change; deliver asynchronously.
- Avoid sending external email/SMS inside the enrollment transaction.
## Core invariants

1. Active enrollment count for an offering never exceeds capacity.
2. A student cannot have duplicate active enrollment in the same offering.
3. An enrollment cannot be committed for a closed/cancelled offering or outside its registration window.
4. Prerequisite, credit-limit and timetable checks are validated before commit; a UI preflight is advisory, not a reservation.
5. Grade and attendance writes require role + object-level authorization and produce audit events.
6. A failed enrollment leaves no partial seat reservation, enrollment row, or success notification.
7. A retry with the same idempotency key does not create a second logical operation.
8. Cached catalogue data can be stale within a documented TTL; capacity and grades are read from the authoritative database for decisions.

## First vertical slice

Implement only Student, Course, CourseOffering and Enrollment first. Provide:
- list/search open offerings
- get offering capacity and current seats remaining
- submit enrollment
- list current student's enrollments
- drop enrollment (if time allows; design the lifecycle first)
- administrator seed-data script for synthetic students/courses/offerings
- API tests plus real-PostgreSQL concurrency test

Attendance, grades, notifications and richer profile fields follow after the registration transaction is reliable.
