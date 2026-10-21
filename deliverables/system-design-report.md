# Scalable Student Information System — System Design Report

## 1. Problem statement

Build a student information system that supports student accounts and profiles, course discovery and registration, attendance, assessments/grades, timetable, and notifications. The system must remain correct under concurrent requests and expose measurable behaviour as load increases.

## 2. Design thesis

**Correctness before scale; measured complexity before distributed complexity.** A cache, rate limiter or shard router may demonstrate scale, but none replaces transactional correctness in the authoritative database.

## 3. Architecture

Browser dashboard and Locust workloads call a FastAPI modular monolith. The API uses PostgreSQL for academic records. The process-local token bucket limits request bursts; the TTL/LRU cache serves autocomplete; separate experimental endpoints demonstrate consistent hashing, in-memory sharding, ID generation, short links, crawling and metrics.

The baseline deploys one application and one PostgreSQL database. In-memory components are isolated experiments, not production-grade distributed services.

## 4. Data model

- Student: unique student number and email.
- Course: unique course code, title and credits.
- CourseOffering: one term/section of a course, capacity, enrollment counter and registration status.
- Enrollment: student + offering, status, idempotency key and timestamp.
- UserAccount: password hash, role and student link.
- AttendanceRecord: unique student + offering + session date.
- Assessment and Grade: assessment maximum and one grade per student/assessment.
- TimetableEvent: offering, day/time, room and term.
- AcademicNotification: per-student message, creation and read timestamps.

Course and CourseOffering are separate: a catalog course may be offered in several terms or sections.

## 5. Critical correctness invariant

For every offering: 0 <= enrolled_count <= capacity.

An enrollment attempt executes a conditional database update that increments enrolled_count only when the offering is OPEN and enrolled_count < capacity. The enrollment insert shares the same transaction. If the insert fails, the reservation update rolls back. Unique constraints defend against duplicate enrollment and idempotency-key reuse. A preflight read is advisory only; the database operation is authoritative.

Dropping an enrollment transitions ENROLLED to DROPPED once and decrements the counter in the same transaction. A repeated drop is rejected. A partial unique index allows only one ENROLLED enrollment per student/offering; after dropping, a student may enroll again with a new idempotency key. The original idempotency key remains permanently bound to its original request.

## 6. Required system-design components

| Component | Prototype implementation | Evaluation metric | Important limitation |
|---|---|---|---|
| Rate limiter | Thread-safe process-local token bucket middleware | accepted/rejected requests; 429 rate | Per process, not shared across workers |
| Sharding | In-memory key/value records assigned to ring nodes | record count per shard; key readability | Does not shard PostgreSQL tables |
| Consistent hashing | SHA-256 ring with virtual nodes | key movement after node changes | Ring changes do not migrate or replicate records |
| Key-value store | Bounded TTL/LRU cache for autocomplete | hit/miss rate and latency | Process-local; TTL-based invalidation |
| Unique ID generator | 64-bit time/worker/sequence generator | IDs/s, uniqueness in batch | Worker coordination and clock policy needed across hosts |
| URL shortener | Random short codes persisted in PostgreSQL and HTTP redirects | creation and redirect latency | No expiry, analytics, or abuse policy yet |
| Web crawler | Bounded same-host HTTPS crawler | pages/sec, errors, frontier size | Small educational crawler, not distributed |
| Autocomplete | Prefix search over course code/title plus TTL cache | latency, top-k relevance | No ranking or typo tolerance |

## 7. API surface

The API explorer at /docs lists the endpoint contract. Key routes include:
- /auth/register, /auth/login, /auth/me
- /students, /courses, /offerings
- /offerings/{id}/enroll, /enrollments/{id}/drop
- /attendance, /assessments, /assessments/{id}/grades
- /timetable, /notifications
- /autocomplete, /short-links, /s/{code}
- /system-design/route/{key}, /system-design/sharded-records/{key}
- /system-design/ids, /system-design/crawler/run
- /system-design/http-metrics, /system-design/metrics

## 8. Workload plan

1. **Read-heavy discovery:** search courses, autocomplete and list offerings. Run at 10, 50 and 100 users; report throughput, p50/p95/p99, error rate and cache hit/miss.
2. **Profile and academic reads:** student profile, enrollments, grades and timetable. Use a deterministic synthetic dataset; compare broad versus selective reads.
3. **Enrollment burst:** many distinct students claim a low-capacity offering concurrently. Report successes, 409 responses and invariant violations. Capacity violations must remain zero.
4. **Write mix:** student creation and attendance/grade writes. Track database latency and error codes.
5. **Component comparison:** autocomplete cache cold/warm; rate limiter under burst; consistent-hash ring with 3 versus 4 nodes and moved-key fraction.

## 9. Metrics and reproducibility

For each run, save the OS/hardware, Python/DB versions, data size, request mix, users, spawn rate, duration, throughput, p50/p95/p99, failure rate, CPU/memory, DB connections and invariant checks. Repeat after warm-up. Never compare runs with different workload mixes as controlled experiments.

The controlled Locust runs below are the current post-RBAC baseline. Each run used 10 users for 20 seconds (except the separately noted clean profile-read run, also 20 seconds). These are single-run local observations, not production capacity claims.

## 10. Security and limitations

This is an academic prototype, not production-ready software. Staff-only academic mutations and student record reads enforce role/self-access checks. Staff promotion is a trusted local CLI operation. Token revocation/refresh and production identity controls are not implemented. Do not expose it publicly or use real student data. Tokens require SIS_TOKEN_SECRET in production; local development uses the ignored .env file for a random secret. The rate limiter, cache, synthetic shard records and metrics are process-local; short-link mappings are persisted in PostgreSQL. The crawler has network safety bounds but needs independent security review before use outside coursework.

## 11. Next improvements

- Add token revocation/refresh and a production identity provider; strengthen auth/rate-limit abuse tests.
- Move rate-limit and cache state to Redis and benchmark a shared limiter.
- Repeat the baseline several times at longer durations and capture CPU/memory/database pool time series.
- Implement data migration/replication and failure handling before claiming real sharding.
- Add waitlist lifecycle and a transactional outbox; short-link mappings are already persisted in PostgreSQL.
- Add a CI test workflow.

## 12. Controlled post-RBAC local benchmark (2026-10-19)

Environment: Ubuntu laptop, Intel Core i5-1135G7, approximately 7.1 GiB host memory; PostgreSQL 17 in Podman; 1,000 synthetic students, 100 courses and 200 offerings. Locust workloads used 10 users, a 2-user/second spawn rate and 20-second time limits. The rate limiter was disabled for baseline workloads and enabled only for the explicit overload run. The authenticated profile-read run reused a pre-created synthetic account, so it excludes registration/login setup calls.

| Workload | Requests | Throughput req/s | p50 ms | p95 ms | Failures |
|---|---:|---:|---:|---:|---:|
| Course search/list/offering mix | 681 | 35.82 | 5 | 10 | 0 |
| Authenticated profile/enrollment/grade/timetable reads | 669 | 35.27 | 5 | 12 | 0 |
| Student account registration writes | 370 | 19.47 | 60 | 83 | 0 |
| Autocomplete prefixes, cache enabled | 675 | 35.55 | 2 | 5 | 0 |
| Autocomplete prefixes, cache disabled | 659 | 34.68 | 5 | 10 | 0 |
| Course-search overload, rate limiter enabled | 676 | 35.61 | 4 | 10 | 243 HTTP 429 |

### Interpretation and component metrics

The autocomplete cache-on run reported mean latency 2.88 ms versus 5.85 ms with caching disabled (about 50.8% lower); median latency fell from 5 ms to 2 ms and p95 from 10 ms to 5 ms. Both cache runs had zero failed requests. This is a short single-run observation, not statistically strong proof that the same percentage improvement will hold for every prefix or deployment.

The registration workload includes PBKDF2 password hashing, so its latency is intentionally higher than read-only requests. The 20-second rate-limit overload run rejected 243 of 676 requests (35.95%) with HTTP 429. That demonstrates admission control under this offered load, but the configured quota is too restrictive for this traffic mix; it should be tuned against legitimate demand and protected-service latency.

The consistent-hash experiment moved 277 of 1,000 sampled keys (27.7%) after adding a fourth node with the current ring configuration. This is an observed sample, not a universal guarantee. The endpoint warns that routing changes do not migrate or replicate the synthetic shard records.

### Resource and crawler validation caveats

A separate API-process sample during local 10-user load observed approximately 7.4% average CPU of one logical CPU (sampled peak 16%) and roughly 90,660 KiB RSS (about 88.5 MiB). This is process-level sampling, not total host/PostgreSQL consumption or continuous peak telemetry. The database container and Locust process need separate time-series sampling for a complete capacity model.

A live crawl of https://example.com could not be verified in this environment because DNS resolution was unavailable. Crawler parsing and same-host frontier behavior are tested with a mocked HTTPS response; public-network behavior should be validated in a network-enabled environment.

These runs are single-run local baselines, not production capacity claims. Repeat each workload several times at longer durations and record API, database and load-generator resource time series before drawing scale conclusions.

## 13. Next improvements

- Add token revocation/refresh and a production identity provider; strengthen authentication and rate-limit abuse tests.
- Move rate-limit and cache state to shared Redis and benchmark the shared implementation.
- Repeat baselines several times at longer durations and capture API, PostgreSQL and load-generator resource time series.
- Implement data migration/replication and failure handling before claiming real sharding.
- Add waitlist lifecycle and a transactional outbox for notifications.
- Review crawler DNS-pinning/SSRF protections before use outside coursework.
- Extend CI to run the PostgreSQL concurrency suite against an ephemeral database.


## 14. Current verification snapshot — 20 October 2026

This section records the verification performed for the current local runtime. It supersedes any implication that every dependency was available at the time of this snapshot.

### Environment and isolation

- React/Vite source build: `npm run build` completed successfully (TypeScript build and Vite production bundle).
- The browser dashboard was served from the existing production build by the SIS FastAPI app on `127.0.0.1:8000` for same-origin UI/API demonstration.
- Port `5173` was occupied by an unrelated Atlas application, and port `8080` by an unrelated Agentic OS process. Neither was treated as the SIS service.
- PostgreSQL was unavailable on `127.0.0.1:5432`; the current live SIS API was therefore launched on port `8000` against an isolated temporary SQLite database at `/tmp/sis_audit_test.db`. No project UI source or existing project database was modified for this audit.

### Results

| Check | Result | Scope / interpretation |
|---|---|---|
| Automated test suite | 21 passed | SQLite-backed test run; does not establish PostgreSQL concurrency correctness |
| HTTP/API smoke checks | 12/12 passed | Health, OpenAPI, course listing, autocomplete, ID generation, ring, validation, registration/login, `/auth/me`, invalid-password rejection, staff-role denial |
| Frontend production build | Passed | TypeScript and Vite build completed |
| Ruff static checks | Passed | `app`, `tests`, `scripts`, and `migrations` |
| Alembic upgrade + drift check | Passed | Clean, isolated SQLite migration database; no pending model/schema changes |
| Browser navigation | 7/7 sections captured | Overview, catalogue, enrollment, records, account, faculty, system observability; desktop navigation and mobile drawer exercised |
| Browser JavaScript errors | 0 observed | During screenshot/navigation run; this is not a full accessibility audit |
| PostgreSQL service availability | Failed / unavailable | No listener on port 5432; PostgreSQL integration tests could not be run against PostgreSQL in this snapshot |
| PostgreSQL concurrency invariant | Not re-verified in this snapshot | Historical result is documented in the 19 October benchmark section; it must not be presented as a fresh 20 October test |
| Live public crawler | Not verified | The existing benchmark notes DNS/network limitations; crawler unit coverage uses mocked HTTPS responses |

### Current conclusion

The application code passes its current SQLite suite and targeted API checks. The frontend production bundle, static checks, and isolated SQLite migrations pass. **The complete PostgreSQL-backed SIS is not currently operational or fully verified because PostgreSQL is not running.** The 8080 listener is a separate application, not SIS. The next release gate is to start the intended PostgreSQL 17 service, apply migrations to a dedicated SIS database, seed synthetic records, and rerun the full suite—including concurrent enrollment tests—against PostgreSQL before claiming end-to-end production-database readiness.

### UI evidence captured

The screenshot collection in `deliverables/screenshots/` was captured from the current React production build without changing UI source or CSS. It contains a desktop overview, each of the six additional application sections, a mobile overview, mobile navigation, faculty workspace on mobile, and an alternate-theme overview. The UI was connected to the isolated temporary SQLite API for this demonstration; screenshots are interface evidence, not proof of PostgreSQL availability.

### Design references used for report/poster composition

- Nielsen Norman Group, *Visual Hierarchy in UX*: https://www.nngroup.com/articles/visual-hierarchy-ux-definition/ — scale, contrast, grouping, and clear attention order.
- Nielsen Norman Group, *5 Principles of Visual Design in UX* (reviewed 1 September 2026): https://www.nngroup.com/articles/principles-visual-design/ — scale, hierarchy, balance, contrast, and Gestalt.
- GOV.UK Design System, *Type scale*: https://design-system.service.gov.uk/styles/type-scale/ — readable, consistent type scale and line-height rhythm.
- GOV.UK Design System, *Button*: https://design-system.service.gov.uk/components/button/ — clear action labels, hierarchy, and minimum text contrast.
- UK Home Office User-Centred Design Manual, *Layout and typography*: https://design.homeoffice.gov.uk/accessibility/page-structure/layout-typography — readable typography, reflow, and responsive layout considerations.

These are primary design-system and established UX guidance sources, not claimed as SIS implementation dependencies or endorsements.

## 15. PostgreSQL re-verification — 20 October 2026

This is the latest verification record and supersedes the earlier Section 14 runtime conclusion. PostgreSQL was found running in a rootless Podman container on the host, but its published port was not accepting host connections. To avoid changing or dropping the existing `sis` database, a separate PostgreSQL 17.11 verification container and database were created on `127.0.0.1:55432/sis_verify`.

### Database setup and isolation

- PostgreSQL: 17.11 (`postgres:17-alpine`), accepting connections.
- Demo database: `sis_verify` in a dedicated temporary verification container; it contains the clean synthetic UI dataset and a local demo staff account. No schema or rows in the existing `sis` database were altered.
- Test database: `sis_test_final`, a separate empty PostgreSQL database in the same container, used for the final migration, full-suite and schema-drift checks.
- Alembic migrations: all three revisions applied successfully to both fresh databases.
- Alembic schema drift check: passed against `sis_test_final`; no new upgrade operations detected.
- Synthetic UI dataset: 1,000 synthetic students, 100 synthetic courses and 200 course offerings. A local demo staff account was created with a generated temporary password.
- The application was started on `127.0.0.1:8000` against `sis_verify` for API smoke tests and refreshed UI captures. The React source and CSS were not edited.

### Verification results

| Check | Result | Evidence / scope |
|---|---|---|
| Full automated suite | **23 passed** | `uv run pytest -q`, connected to isolated PostgreSQL database |
| Concurrent seat-capacity test | **Passed** | 20 distinct students compete for 5 seats; capacity invariant held |
| Duplicate-enrollment race | **Passed** | Concurrent duplicate requests leave one active enrollment and one counter increment |
| Alembic migrations | **Passed** | Fresh database upgraded to current head |
| Alembic model/schema drift | **Passed** | No new upgrade operations detected |
| Ruff | **Passed** | `app`, `tests`, `scripts`, and `migrations` |
| Frontend production build | **Passed** | TypeScript and Vite production build |
| Live API smoke checks | **5/5 passed** | `/health`, `/openapi.json`, `/courses`, `/autocomplete?q=sy`, `/system-design/ids` returned HTTP 200 |
| Browser UI capture | **7/7 desktop sections** | Overview, catalogue, enrollment, records, account, faculty, system observability |
| Browser JavaScript errors | **0 observed** | During the refreshed screenshot run |

The full suite emitted one upstream Starlette/httpx deprecation warning from the installed test client; it did not cause a test failure. It is a maintenance warning rather than a failing application test.

### Current conclusion

The full automated suite now passes against PostgreSQL, including both concurrency tests. Fresh migrations and schema drift checks pass, the frontend production build passes, and the live PostgreSQL-backed API smoke checks return successfully. The interface screenshots in Appendix A were refreshed from the current production frontend connected to the isolated PostgreSQL verification database and synthetic data.

This is a local verification result, not a production deployment certification. The original host PostgreSQL container's port publication was not reachable from the host in this session, so a separate verification container was used on port 55432. The temporary verification container is left available for inspection and can be stopped when no longer needed. The live public crawler remains unverified because DNS/network access was not established, and the 19 October Locust figures remain historical single-run local measurements rather than fresh performance results.

### Reproduction commands

From `sis-app`, use the verification database URL (adapt the port if you recreate the container) and run:

```bash
DATABASE_URL='postgresql+psycopg://sis:<local-test-password>@127.0.0.1:55432/sis_verify' uv run alembic upgrade head
DATABASE_URL='postgresql+psycopg://sis:<local-test-password>@127.0.0.1:55432/sis_verify' uv run alembic check
DATABASE_URL='postgresql+psycopg://sis:<local-test-password>@127.0.0.1:55432/sis_verify' SIS_RATE_LIMIT_ENABLED=false uv run pytest -q
uv run ruff check app tests scripts migrations
cd frontend && npm run build
```


## 16. Editorial deliverables and visual QA — 20 October 2026

The earlier poster/report presentation was replaced with a new editorial layout after visual inspection showed the original poster was too text-heavy and the report screenshots were not presented at useful scale. The poster was redesigned on 21 October 2026 using a landscape A3 grid, dark technical masthead, teal section bands, high-contrast metric cards, an architecture diagram, the transactional enrollment story, and actual Postman/JMeter evidence. The current poster is `SIS-System-Design-Poster.pdf` (one A3 landscape page). Its editable source is `poster-editorial.html`, built reproducibly by `scripts/build_poster.mjs`. The report source remains separate.

### Design method

- Consulted Carnegie Mellon University Libraries poster design/content guidance, NIH scientific poster guidance, Harvard Catalyst poster design guidance, Nielsen Norman Group visual hierarchy, and UK DWP research report guidance.
- Rebuilt the poster around one main finding, a live dashboard image, large verification metrics, a React → FastAPI → PostgreSQL architecture path, a seat-capacity invariant, and a visual concurrency flow. This is a new layout, not a recolouring of the previous poster.
- Rebuilt the report as a paginated technical case study: executive finding, architecture, transactional correctness, test matrix, component boundaries, a dedicated visual QA finding, six captioned interface figures, and references/reproduction commands.
- Re-captured screenshots from the actual production frontend using Playwright at a stable 1600 × 1100 desktop viewport. The script waits for UI transitions and API responses, exercises student login, a successful enrollment, grade retrieval, staff login, and the system autocomplete experiment. Browser JavaScript errors during these runs: zero.
- Removed the previous full-page/duplicate screenshot set from the showcase directory. The remaining primary screenshots correspond to actual workflows; synthetic demo data is labelled as such.

### Additional visual QA findings

- Initial QA at 390 × 844 found that the mobile menu opened while the dashboard remained horizontally displaced: `.main-area` retained the desktop `margin-left` even after the sidebar became an overlay. This was repaired with a narrowly scoped `@media (max-width: 760px)` override setting `.main-area` margin-left to zero and constraining it to the viewport. No component markup, typography, colors, glass effects, or desktop layout rules were changed. Playwright regression checks on the production-served build passed at 320, 390, 430, 768, 1024, and 1440 px; the mobile drawer was also opened and dismissed at 320, 390, 430, and 700 px. The document width matched the viewport and no browser JavaScript errors were observed. `screenshots/qa-mobile-layout-fixed.png` records the repaired 390 × 844 viewport; the original `qa-mobile-layout-offset.png` is retained as before-fix evidence.
- The ID API returned ten distinct 64-bit IDs in raw JSON and reported zero collisions. The browser's JSON result viewer parses large integers as JavaScript `Number`, which rounds values beyond the safe-integer range and makes distinct IDs appear repeated. This was a client interoperability defect rather than an ID collision: on 21 October the API was changed to serialize 64-bit IDs as strings, and a regression assertion now verifies the string contract. The current Postman collection confirms 25 IDs are unique after JSON parsing.
- The system observability screenshot uses the autocomplete API response rather than a misleading rounded display of large IDs.

### Current interpretation

The new poster and report are based on real application captures and test results, with synthetic data clearly identified and limitations stated. The poster is designed for quick scanning; the report preserves implementation details, reproducible checks and known defects. The mobile visual defect discovered during the first pass has since been repaired with a narrowly scoped responsive CSS override and rechecked in Playwright. The visual system and desktop layout remain unchanged.

### Design references

- Carnegie Mellon University Libraries, *How to Make a Science Research Poster: Design*: https://guides.library.cmu.edu/scienceposters/design
- Carnegie Mellon University Libraries, *How to Make a Science Research Poster: Content*: https://guides.library.cmu.edu/scienceposters/content
- National Institutes of Health, *Creating a Scientific Poster*: https://www.training.nih.gov/creating-a-scientific-poster/
- Harvard Catalyst, *Poster Design*: https://catalyst.harvard.edu/writing-communication-center/poster-design/
- Nielsen Norman Group, *Visual Hierarchy in UX*: https://www.nngroup.com/articles/visual-hierarchy-ux-definition/
- UK Department for Work & Pensions, *Research Report Guidance* (updated 10 April 2026): https://www.gov.uk/government/publications/dwp-research-reports-style-guide/dwp-research-reports-guidance


## 17. Previous professional LaTeX report edition — 20 October 2026 (superseded)

The report was rebuilt as `SIS-System-Design-Report-Professional-2026-10-20.pdf` from `report-professional.tex` using LaTeX. The 20-page A4 technical report now includes a controlled title page, abstract, contents, lists of figures and tables, numbered technical sections, running headers/footers, original vector diagrams, a structured verification matrix, real application screenshots, references, and a reproduction appendix. The canonical `system-design-report.pdf` was synchronized to this edition.

The layout follows the technical-report structure and figure/table practices documented by Carnegie Mellon University's Robotics Institute and the NIST Technical Series author guidance. The report uses consistent 11 pt body text, measured margins, booktabs-style tables, concise figure captions, numbered equations, and a restrained ink/teal palette. Architecture and transaction diagrams are vector graphics rather than screenshots of diagrams.

The report was compiled twice with pdfLaTeX to resolve cross-references. The resulting PDF is 20 A4 pages. Text extraction and metadata checks completed. It records 23 passing tests against the isolated PostgreSQL 17.11 verification database, while retaining explicit caveats for historical Locust measurements, process-local experiments, the unverified public crawler, and non-production readiness.

### Report design references
- Carnegie Mellon University Robotics Institute, *Technical Report Format*: https://www.ri.cmu.edu/technical-report-format/
- National Institute of Standards and Technology, *NIST Technical Series Publications Author Instructions*: https://www.nist.gov/nist-research-library/nist-technical-series-publications-author-instructions
- PostgreSQL documentation, *Transaction Isolation*: https://www.postgresql.org/docs/16/transaction-iso.html
- PostgreSQL documentation, *Explicit Locking*: https://www.postgresql.org/docs/17/explicit-locking.html

These references informed the document structure and technical explanations. They are not endorsements of the project.


## 18. Postman and Apache JMeter verification — 21 October 2026

Postman Desktop 12.33.2 was installed; its exported collection was executed through Newman 6.2.3. Apache JMeter 5.6.3 was used for paced and unpaced API workloads. The API ran at `127.0.0.1:8000` against the existing development database and synthetic data. The collection creates one uniquely named synthetic student account. The retained Newman JSON is sanitized: response bodies and bearer tokens are removed.

| Check | Result | Scope |
|---|---|---|
| Postman collection / Newman | 13 requests, 24/24 assertions passed, 24 ms average response time | Health, catalogue/offerings, autocomplete, IDs, ring/metrics, authentication, role denial, invalid credentials. Expected 401/403 outcomes are pass conditions. |
| JMeter paced read-only baseline | 10 threads, 2 s ramp, 20 s, 185 samples, 0 errors, 3.91 ms mean, 3 ms median, 8 ms p95, 9.83 requests/s | Seven read-only endpoints; a short single run on the same laptop as the API and database. Not a production-capacity estimate. |
| JMeter unpaced overload | 69,197 samples; 58,033 HTTP 429 (83.87%); 11,164 HTTP 200 | Deliberately unpaced stress to observe admission control. Keep separate from the baseline and do not treat throughput as sustainable capacity. |
| Resource-sampled paced repeat | 185 samples; 0 errors; mean 7.37 ms; p95 20 ms; 9.87 req/s | `pidstat`: API CPU mean 2.65%, peak 5.0%, RSS 14,436–30,876 KiB. `podman stats`: PostgreSQL container 11.35–21.58 MB memory, about 0.26% CPU in 20 one-second samples. This excludes load-generator and host-wide metrics. |
| PostgreSQL automated tests | 23 passed | Rerun against a dedicated test database after ID serialization change, including capacity and duplicate-enrollment races. |
| Ruff | Passed | `app`, `tests`, `scripts`, and `migrations`. |

Evidence assets are under `deliverables/testing-tools/` and `deliverables/screenshots/tool-verification/`. `SIS-Functional-API-Verification.postman_collection.json` is the importable collection; `SIS-ReadOnly-API-Workload.jmx` is the JMeter plan. JMeter raw JTL and HTML dashboards are retained separately for the baseline and overload run.

The Postman run caught a client interoperability defect: 64-bit IDs returned as JSON numbers exceed JavaScript's safe integer range. The API now serializes them as strings, and a regression assertion checks the contract. The JMeter plan is read-only and does not replace PostgreSQL transaction tests. Rate limiting, cache, ID generation and telemetry are process-local; these runs do not demonstrate multi-worker coordination or production scalability.


## 19. Poster redesign — 21 October 2026

The new A3 landscape poster combines the strongest elements from the supplied references: a dark high-contrast title band, a restrained lime accent, teal section headers, a structured three-column evidence layout, compact metric cards, clean diagrams, and real interface/testing screenshots. Content is organized around six questions: architecture, data integrity, concurrency, functional API verification, measured load behaviour, and engineering limitations.

It reports the latest verified values: 23/23 PostgreSQL-backed automated tests; 24/24 Postman/Newman assertions across 13 requests; 185 JMeter baseline samples with zero errors, 3.91 ms mean and 8 ms p95; and a separate unpaced overload run in which 83.87% of requests returned HTTP 429. Resource samples are labelled as local process/container observations. Baseline and overload runs are deliberately separated, and the poster explicitly says these measurements are not production-capacity certification.

Source: `poster-editorial.html`; builder: `scripts/build_poster.mjs`; preview: `poster-editorial-preview.png`; final: `SIS-System-Design-Poster.pdf`. The poster was exported as one A3 landscape page and checked for missing images and clipped panel content.
