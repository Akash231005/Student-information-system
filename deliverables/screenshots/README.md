# Orbit SIS — verified screenshot evidence

Captured on 20 October 2026 from the actual React production build served by FastAPI at `127.0.0.1:8000`, connected to an isolated PostgreSQL 17.11 verification database. Desktop captures use a fixed 1600 × 1100 viewport, wait for navigation transitions and API activity, and were individually inspected before inclusion. The responsive shell offset has since been repaired with a narrowly scoped CSS override; no component markup or visual styling was redesigned.

## Product/demo screenshots

| File | What it proves / shows |
|---|---|
| `00-overview-viewport.png` | Dashboard loaded with course counts, available seats and API health status. |
| `02-courses-desktop.png` | Course catalogue populated from the synthetic PostgreSQL dataset. |
| `02-enrollment-desktop.png` | Enrollment workflow before submission. |
| `03-enrollment-confirmed.png` | Successful enrollment, returned API payload and active registration row. |
| `04-academic-records.png` | Academic-record request returning synthetic assessment results. |
| `02-account-desktop.png` | Student sign-in succeeded; profile and account protection details loaded. |
| `07-faculty-workspace.png` | Faculty/admin workspace after staff sign-in; no writes were performed during capture. |
| `06-system-observability.png` | System playground after autocomplete request; returned course JSON is visible. |

The screenshots use **synthetic demonstration data only**. They are not real student records. The 23-test PostgreSQL suite, migration checks and concurrency results are separately documented in the report.

## QA-only findings (not for showcase use)

- `qa-mobile-layout-offset.png` — before-fix capture showing the original 390 × 844 displacement; retained for audit history only.
- `qa-mobile-layout-fixed.png` — after-fix capture at 390 × 844. The main content starts at x=0 and fits the viewport.
- `qa-mobile-navigation-overlay.png` — mobile drawer state, retained only as debugging evidence; it is not presented as a polished product screenshot.

The regression run checked 320, 390, 430, 768, 1024 and 1440 px widths; the drawer opened and closed at 320, 390, 430 and 700 px. The document width matched each viewport and no browser JavaScript errors were observed. Mobile captures remain QA evidence, not poster/showcase material.


## Tool-assisted verification screenshots — 21 October 2026

| File | What it shows |
|---|---|
| `tool-verification/postman-api-verification.png` | Rendered evidence report from the actual Postman collection executed with Newman: 13 requests and 24/24 assertions passed. |
| `tool-verification/jmeter-baseline-dashboard.png` | Apache JMeter HTML dashboard from a paced 20-second read-only run: 185 samples, zero errors, mean 3.91 ms, p95 8 ms. |
| `tool-verification/jmeter-rate-limit-overload.png` | Apache JMeter dashboard from an intentionally unpaced overload: 83.87% HTTP 429. This is overload/admission-control evidence, not baseline performance. |
| `tool-verification/jmeter-resource-sample-dashboard.png` | Second paced JMeter run associated with sampled API CPU/RSS and PostgreSQL container resource logs. |

These captures are rendered from actual run outputs. The Postman image is a collection-run evidence summary (Newman), not a screenshot of the Postman desktop application window.


## Fresh tool rerun screenshots — 21 October 2026

`tool-verification/rerun-20261021/` contains fresh evidence captured from a newly executed Newman run and newly generated Apache JMeter HTML dashboards. The Newman image is explicitly an evidence summary from the collection-run JSON, not a Postman desktop screenshot. The paced JMeter dashboard shows 185 samples with zero errors (mean 4.95 ms, median 4 ms, p95 10 ms). The separate unpaced run shows the actual overload mix: 40,372 HTTP 429, 8,081 HTTP 200, and six socket timeouts among 48,459 samples. Do not label all failed samples as HTTP 429.
