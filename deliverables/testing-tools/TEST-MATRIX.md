# SIS tool-assisted verification matrix

## Installed tools
- Apache JMeter 5.6.3: `~/Applications/apache-jmeter-5.6.3/`; official SHA-512 check: passed. Official download: https://jmeter.apache.org/download_jmeter.cgi
- Postman Desktop 12.33.2: `~/Applications/Postman/`; official Linux download endpoint used. Official download: https://www.postman.com/downloads/
- Newman 6.2.3: used to execute the exported Postman collection and retain assertion results.

## Tool roles
- **Postman**: endpoint-by-endpoint functional checks, auth/authorization, validation, and repeatable collection runs.
- **Apache JMeter**: controlled concurrent read workload; response-time distribution, throughput, errors, and CSV/JTL output.
- **Locust (already in the project environment)**: retain for custom user journeys and controlled cache/rate-limit comparisons; do not discard its historical results.
- **pytest + PostgreSQL**: authoritative correctness and concurrent enrollment invariants; JMeter alone cannot prove these.
- **Playwright (already in frontend dependencies)**: responsive UI and browser end-to-end checks.

## Included assets
- `postman/SIS-Functional-API-Verification.postman_collection.json` — 13 requests with assertions. Registration creates one uniquely named synthetic account.
- `jmeter/SIS-ReadOnly-API-Workload.jmx` — paced baseline: 10 virtual users, 2-second ramp, 20-second duration, 1-second think time, seven read-only endpoints.
- `jmeter/SIS-Rate-Limit-Overload-Unpaced.jmx` — intentionally unpaced overload plan used for rate-limit behavior; run separately and interpret only as overload evidence.

## Run
1. Start the SIS API on `127.0.0.1:8000` using the development database and verify `/health`.
2. Import the Postman collection and set `baseUrl` if needed. Run requests in order. Keep only synthetic data.
3. Run JMeter in non-GUI mode and create an HTML dashboard plus raw JTL; do not use the same output directory twice.
4. Capture real screenshots of the Postman results and JMeter dashboard, and retain raw output files.

## Required evidence beyond these two tools
- PostgreSQL race test: 20 concurrent students competing for 5 seats => exactly 5 accepted and 15 conflict responses; verify database rows and seat counter.
- Duplicate-enrollment idempotency race: exactly one active row and one counter increment.
- At least three workload types; report p50/p95/p99, throughput, error rate and resource usage. Repeat comparable runs at least three times if claiming a robust comparison.
- Component evidence: cache HIT/MISS and invalidation; rate-limit 429; unique-ID uniqueness/throughput; consistent-hash key movement; URL-shortener create/redirect; crawler URL validation/frontier behavior; sharded-record route/read and explicit data-loss/migration limitation.
- DB migration/schema drift, auth/role/record ownership checks, frontend responsive checks, and a recorded end-to-end demo.

## Limitations
JMeter plan is intentionally read-only. It does not create students or courses, mutate shard-ring nodes, or test capacity correctness. Its local load result is not a production scalability claim. Crawler success must not be reported as a live crawl unless a real permitted fetch is verified.


## Recorded results — 21 October 2026
- Postman/Newman: **13 requests; 24/24 assertions passed**. Sanitized summary: `postman/run-20261021-report.html`; machine-readable summary: `postman/run-20261021.json` (response bodies and bearer tokens redacted).
- JMeter paced baseline: **185 samples; 0 errors; mean 3.91 ms; median 3 ms; p95 8 ms; 9.83 req/s**. See `jmeter/baseline-20261021/html-report/` and `results.jtl`.
- JMeter unpaced overload: **69,197 samples; 58,033 HTTP 429 (83.87%); 11,164 HTTP 200**. See `jmeter/overload-20261021/html-report/`. This is a separate admission-control experiment, not a performance baseline.
- PostgreSQL automated suite after ID serialization fix: **23 passed**; Ruff passed.
- Screenshots: `../screenshots/tool-verification/`.

- Resource-sampled paced repeat: 185 samples, 0 errors, mean 7.37 ms, p95 20 ms, 9.87 req/s. `pidstat` observed API CPU mean 2.65% / peak 5.0% and RSS 14,436–30,876 KiB; `podman stats` sampled PostgreSQL container memory 11.35–21.58 MB and CPU about 0.26%. These are sampled local process/container values, not host-wide or production capacity measurements. Raw samples are under `jmeter/resource-sample-20261021/`.


## Fresh rerun evidence — 21 October 2026, 11:46–11:50 IST

A fresh run was executed against the live local API at `127.0.0.1:8000`; outputs are kept under `rerun-20261021/` to distinguish them from earlier evidence.

- **Postman collection via Newman 6.2.3:** 13 requests; 24 assertions; 0 assertion failures. Average response time reported by the runner: 20 ms. Requests included health, course/offerings, autocomplete, IDs, ring/metrics, auth failures, synthetic registration/login, identity, and student-role denial.
- **JMeter 5.6.3 paced baseline:** 10 threads, 2-second ramp, 20-second duration, 1-second constant timer; 185 samples, 0 errors; mean 4.95 ms, median 4 ms, p95 10 ms, throughput 9.84 requests/s. All observed status codes were HTTP 200.
- **JMeter unpaced overload:** 48,459 samples; 40,372 HTTP 429, 8,081 HTTP 200, and 6 socket timeouts; total failed-sample fraction 83.32%. The timeouts are explicitly retained in the result and are not described as HTTP 429. This is an intentionally excessive local workload, not a baseline.
- Fresh dashboard screenshots: `../screenshots/tool-verification/rerun-20261021/`. `postman-newman-run.png` is an HTML evidence summary rendered from Newman JSON, **not** a screenshot of the Postman desktop application. JMeter screenshots are rendered from the JMeter-generated HTML dashboards.
- Raw evidence: `postman/run.json`, `postman/console.log`, `jmeter-baseline/results.jtl`, `jmeter-baseline/html-report/statistics.json`, `jmeter-baseline/jmeter.log`, `jmeter-overload/results.jtl`, `jmeter-overload/html-report/statistics.json`, `jmeter-overload/jmeter.log`.

These are single-run localhost measurements. The collection uses synthetic data and creates a new synthetic account. They do not demonstrate production throughput, multi-worker limiter behavior, or production availability.
