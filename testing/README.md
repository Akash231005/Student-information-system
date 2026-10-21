# Native Postman and Apache JMeter test assets

This directory contains the actual importable test definitions and raw outputs, not only screenshots or hand-written summaries.

## Postman

- `postman/SIS-Functional-API-Verification.postman_collection.json` — import this collection directly into Postman Desktop.
- `postman/newman-run-20261021.json` — JSON output from the fresh execution of the collection using Newman 6.2.3.
- `postman/newman-report-20261021.html` — HTML execution report.
- `postman/newman-console-20261021.txt` — runner console output.

The collection targets the local development API at `127.0.0.1:8000`; run only while the intended local SIS API and test database are active. The collection creates synthetic test data. Raw run output is scrubbed of tokens and response bodies for safe sharing.

## Apache JMeter

- `jmeter/SIS-ReadOnly-API-Workload.jmx` — paced, read-only baseline plan.
- `jmeter/SIS-Rate-Limit-Overload-Unpaced.jmx` — intentionally unpaced rate-limit/overload plan.
- Each scenario directory contains the actual `.jtl` sample log, JMeter log, console output, and JMeter-generated HTML `index.html` plus `statistics.json`.

Re-run a plan in non-GUI mode (recommended for load execution):

```bash
jmeter -n -t jmeter/SIS-ReadOnly-API-Workload.jmx \
  -l /tmp/sis-baseline.jtl -e -o /tmp/sis-baseline-report

jmeter -n -t jmeter/SIS-Rate-Limit-Overload-Unpaced.jmx \
  -l /tmp/sis-overload.jtl -e -o /tmp/sis-overload-report
```

Run from the project environment where the API is available at `127.0.0.1:8000`. Do not treat the deliberately unpaced overload plan as a capacity baseline. Its latest run included socket timeouts in addition to HTTP 429 responses.

## Fresh observed run summary

- Newman: 13 requests; 24 assertions; 0 assertion failures.
- JMeter paced baseline: 185 samples; 0 errors; mean 4.95 ms; median 4 ms; p95 10 ms; 9.84 requests/s.
- JMeter unpaced overload: 48,459 samples; 40,372 HTTP 429; 8,081 HTTP 200; 6 socket timeouts. These are localhost, single-run measurements, not production capacity claims.

The exact native files and raw logs are the source of truth; summaries/screenshots are secondary.
