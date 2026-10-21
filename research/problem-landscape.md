# SIS Problem Landscape

## Registration surges
Synchronized registration causes bursts. Retries amplify load. Test saturation, connection pools, query latency and lock contention. Use rate limits, clear overload responses and idempotent writes.

## Last-seat race
Two requests can both read the last seat as available. Enforce capacity transactionally with row locks or atomic conditional updates, plus a unique enrollment constraint. Test 100 concurrent requests against 30 seats.

## Waitlist and eligibility
Prerequisites, credit limits, timetable conflicts and reserved seats affect eligibility. Show actionable rejection reasons. Queue position does not guarantee enrollment.

## Fragmented academic records
Multiple systems can confuse students and staff. Define one authoritative owner per domain and provide a unified dashboard without duplicate editable copies.

## Grade and attendance disputes
Provide validation, role-based writes, correction requests and an audit history with actor and timestamp.

## Timetable staleness
Invalidate affected cache entries after schedule changes. Show last-updated time and notify affected students.

## Notification failure
Persist notifications and delivery state. Retry asynchronously with idempotency keys.

## Slow search and cache stampedes
Debounce autocomplete, index fields, cap results, use TTL/invalidation and protect hot keys.

## Shard skew and privacy
Choose partition keys from query patterns. Apply object-level authorization on every sensitive record lookup.

## Priorities
Must solve correctness, authorization, registration integrity, search and measurement. Then add waitlist, conflict checks, audit history and retry-safe notifications. Crawler and URL shortener are optional.