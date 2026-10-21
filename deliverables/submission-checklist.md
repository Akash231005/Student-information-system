# Submission checklist

## Deliverables
- [x] Runnable FastAPI API and browser dashboard
- [x] PostgreSQL schema and Alembic migrations
- [x] Student registration/login, profile, course search, offerings, enrollment/drop
- [x] Attendance, assessments/grades, timetable and notifications
- [x] Eight required system-design components mapped to observable endpoints
- [x] Three+ workload types and saved Locust CSV outputs
- [x] Architecture, component trade-offs, concurrency invariant and failure-mode analysis
- [x] Automated tests and local lint/migration checks
- [x] System-design report in Markdown and professionally typeset LaTeX PDF (31 pages, including architecture/transaction diagrams, data integrity, architecture decisions, test strategy, release gates, references, and appendices)
- [x] 9-slide presentation and 10-minute speaking outline
- [x] A3 landscape poster PDF
- [x] Demo runbook and synthetic dataset generator
- [x] Reproducible submission ZIP generator and refreshed ZIP archive

## Final local verification — 19 October 2026
- PostgreSQL test suite: **23 passed**
- Ruff: passed
- Alembic upgrade and schema check on clean temporary SQLite and PostgreSQL 17 databases: passed
- API health endpoint: HTTP 200
- Dashboard route: HTTP 200
- Synthetic data seeded: 1,000 students, 100 courses, 200 offerings
- PostgreSQL concurrency invariant: capacity 5 with 20 simultaneous requests resulted in 5 successes and 15 HTTP 409 responses

## Performance evidence caveat
The saved load runs are single-run local measurements using 10 users for 20 seconds. Use the reported throughput and latency as a baseline only, not a production capacity claim. The rate-limiter overload run rejected 243 of 676 requests (35.95%); explain this as admission control and a tuning trade-off.

## Before presenting
1. Start PostgreSQL and the API using deliverables/demo-script.md.
2. Register a synthetic student and create/promote a synthetic staff account using the documented local CLI.
3. Confirm the API dashboard and /docs open.
4. Keep the test output and Locust CSVs ready as backup evidence.
5. Do not use real student records or expose the prototype publicly.

## Explicit limitations to state
- Rate limiting, the autocomplete cache and ID worker slots are backed by one unreplicated Redis node; state is shared across app workers, availability is not.
- Sharded records live in a real two-shard MongoDB cluster (`mongos` + config server). Chunk movement is real; host-level failover is not.
- The consistent-hash ring routes keys but never moves data — `moveChunk` does.
- The prototype does not shard PostgreSQL and does not claim production scalability.
- The crawler honours robots.txt and `Crawl-delay` against the live network, but is same-host, serial, and not hardened against DNS rebinding.
- Token revocation/refresh and production identity integration remain future work.
- Resource sampling is incomplete for making peak CPU/memory claims.


## Professional report and diagram revision — 21 October 2026
- [x] Rebuilt the report in LaTeX using a restrained technical-publication layout.
- [x] Added a formal title page, abstract, table of contents, lists of figures/tables, numbered sections, running headers/footers, and references.
- [x] Added original vector architecture and transaction diagrams, a capacity-results graphic, and actual application screenshots.
- [x] Checked the PDF with pdflatex, PDF metadata/page count, and extracted text.
- [x] Explicitly separated PostgreSQL verification results from historical single-run load measurements and documented known limits.
- [x] Added substantive engineering chapters on domain integrity, architecture decisions, test/evidence quality, benchmark interpretation, security and release gates.
- [x] Replaced generic hand-drawn architecture and transaction figures with editable Graphviz vector assets.
- [x] Regenerated report and poster PDFs from updated sources; report compiles to 31 A4 pages.
- [ ] Final human review of every page and a repeat run of tests against the exact submission snapshot remains recommended.

Latest report: `SIS-System-Design-Report-Professional-2026-10-21.pdf`. Editable source: `report-professional.tex`. The canonical `system-design-report.pdf` is synchronized with this edition.


## API and load-tool verification — 21 October 2026
- [x] Installed Apache JMeter 5.6.3 user-locally and verified its official archive SHA-512 checksum.
- [x] Installed the Postman desktop application user-locally; created an importable Postman collection.
- [x] Ran Postman collection through Newman: 13 requests, 24/24 assertions passed.
- [x] Ran Apache JMeter paced read-only workload: 10 threads, 20 seconds, 185 samples, zero errors; p95 8 ms.
- [x] Repeated the paced workload while sampling API CPU/RSS with `pidstat` and PostgreSQL container CPU/memory with `podman stats`; retained raw samples.
- [x] Ran separate unpaced overload experiment: 83.87% HTTP 429; documented as admission-control evidence, not a baseline.
- [x] Captured the Postman/Newman evidence summary and both JMeter HTML dashboards under `screenshots/tool-verification/`.
- [x] Reran PostgreSQL suite against a dedicated test database after changing 64-bit ID serialization: 23 passed; Ruff passed.
- [x] Fixed JavaScript precision loss by returning 64-bit IDs as JSON strings; regression assertion added.
- [ ] Repeat JMeter baseline at least three times and collect API + PostgreSQL + load-generator CPU/memory before making stronger performance claims.
- [ ] Run explicit JMeter/Postman checks for each academic workflow and component-specific negative cases; current Postman collection is a focused smoke/security collection, not exhaustive endpoint coverage.

Raw results and reusable plans: `testing-tools/jmeter/` and `testing-tools/postman/`. These local tests do not prove production-scale or multi-worker behavior.


## Poster redesign — 21 October 2026
- [x] Redesigned the poster in A3 landscape using the supplied reference direction: dark technical masthead, teal section bands, restrained lime accent, metric cards, structured three-column grid, architecture/transaction diagrams and actual UI/tool evidence.
- [x] Replaced stale load-test claims with the 21 October Postman/JMeter results and labelled local-run limitations.
- [x] Checked all poster images load, all six content panels fit without overflow, and the exported PDF is one A3 landscape page.
- [x] Created the reproducible builder `scripts/build_poster.mjs`, editable source `poster-editorial.html`, preview PNG, dated PDF and canonical `SIS-System-Design-Poster.pdf`.

## Expanded poster revision — 21 October 2026
- [x] Rebuilt the A3 landscape poster around the actual React + FastAPI + PostgreSQL implementation; the SQLite/three-worker figures from the separate generated teammate report were not imported.
- [x] Added introduction/problem framing, architecture and request/data flow, technology stack, four real workflow screenshots with explanatory captions, concurrency transaction steps, the eight required system-design components, measured verification, engineering lessons and next steps.
- [x] Added team names and registration numbers from the supplied team details.
- [x] Verified all seven referenced screenshots load and all six poster panels fit without detected overflow.
- [x] Exported a single-page A3 landscape PDF; editable source is `deliverables/poster-redesign.html`; reproducible builder is `deliverables/scripts/build_poster.mjs`; preview is `deliverables/poster-redesign-preview.png`.
- [x] Regenerated the submission ZIP after updating the poster.
