# Performance evaluation

## Environment and method

- Date: 19 October 2026.
- Host: Lenovo IdeaPad 3 15ITL05, Intel Core i5-1135G7, 8 logical CPUs, Ubuntu-based Linux.
- Python 3.12.13, FastAPI/SQLAlchemy, PostgreSQL 17 in a local Podman container.
- Dataset: synthetic generator configured for 1,000 students, 100 courses, and 200 course offerings.
- Locust: 10 simulated users, spawn rate 2 users/s, 20-second run time per workload.
- All tests ran locally on one machine; network latency between separate hosts is not represented.

These are useful prototype measurements, not a production capacity claim. Runs are short and local,
and the application, load generator, and database share the same machine. Repeat longer tests on a
dedicated load generator and target-like deployment before making scale guarantees.

## Workload results

Numbers below are from the saved Locust aggregate CSVs in `results/verified-20261019-*`.
Response times are milliseconds; throughput is requests per second.
| Workload | Requests | Failures | Median | Mean | p95 | Throughput |
|---|---:|---:|---:|---:|---:|---:|
| Autocomplete, cache disabled | 659 | 0 | 5 | 5.85 | 10 | 34.68 req/s |
| Autocomplete, cache enabled | 675 | 0 | 2 | 2.88 | 5 | 35.55 req/s |
| Course search + offering list | 681 | 0 | 5 | 5.65 | 10 | 35.82 req/s |
| Authenticated profile/grades/enrollments/timetable reads | 669 | 0 | 5 | 7.43 | 12 | 35.27 req/s |
| Student registration writes | 370 | 0 | 60 | 63.63 | 83 | 19.47 req/s |
| Course-search overload with rate limiter enabled | 676 | 243 (35.95%) | 4 | 4.27 | 10 | 35.61 req/s |

### Interpretation

- In the cache comparison, autocomplete mean latency fell by about 50.8% (5.85 ms to 2.88 ms),
  median latency fell by 60% (5 ms to 2 ms), and p95 fell by 50% (10 ms to 5 ms).
- Cache-on throughput was similar (35.55 vs 34.68 req/s). This is a local result; it does not prove
  that caching improves every workload or that the same improvement will hold at larger scale.
- Registration writes are slower because password hashing uses PBKDF2-HMAC-SHA256 with 310,000
  iterations. That is a deliberate security/performance trade-off; auth endpoints need rate limits.
- The overload run produced 243 HTTP 429 responses. This shows admission control working, but a
  35.95% rejection rate also means the offered workload exceeded the configured per-process budget.
  Rate limiting protects the service by rejecting excess demand; it does not make rejected requests succeed.
## Resource sample

A separate 20-second `pidstat` sample of the API worker during a 10-user local load run observed
approximately 7.4% average CPU of one logical CPU (sampled peak 16%) and about 90,660 KiB RSS
(roughly 88.5 MiB). This is process-level sampling, not total host or PostgreSQL resource consumption.
The database container and Locust process need separate resource measurements for a complete capacity
model.

## Correctness and scalability checks

- PostgreSQL capacity test: 20 distinct students concurrently request 5 seats; exactly 5 requests
  succeed and 15 return HTTP 409. Stored enrolled count and active enrollment rows both equal 5.
- Duplicate-enrollment race test: concurrent requests for the same student/offering leave exactly one
  active enrollment and one counter increment.
- Drop/re-enroll test: dropping decrements the seat count once; the student can later enroll again.
- Consistent-hash experiment reports the fraction of synthetic keys that move after adding a node.
  This is routing simulation only; the prototype does not migrate or replicate actual shard data.
- Crawler parsing/frontier behavior is tested with a mocked HTTPS response. A live crawl could not be
  verified here because DNS resolution was unavailable; do not present mock throughput as live crawl throughput.
## Reproduction

Start PostgreSQL and seed the deterministic synthetic dataset, then start two isolated app instances:

```bash
uv run python -m scripts.generate_dataset --students 1000 --courses 100 --offerings-per-course 2
SIS_RATE_LIMIT_ENABLED=false SIS_CACHE_ENABLED=false uv run uvicorn app.main:app --port 8001
SIS_RATE_LIMIT_ENABLED=false SIS_CACHE_ENABLED=true uv run uvicorn app.main:app --port 8002
```

In another terminal, run matching workloads for each condition:

```bash
uv run locust -f locust_autocomplete.py --headless --host http://127.0.0.1:8001 -u 10 -r 2 -t 60s --csv results/cache-off
uv run locust -f locust_autocomplete.py --headless --host http://127.0.0.1:8002 -u 10 -r 2 -t 60s --csv results/cache-on
```

Use fresh output prefixes for every run. Record the commit, dataset, cache/rate-limit flags, run duration,
user count, machine load, and PostgreSQL resource use. Run each scenario at least three times and report
median/variation across runs before using it in the final report.
