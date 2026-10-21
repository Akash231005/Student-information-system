# Performance, Scalability and Failure Evaluation

## Rules
Use synthetic data. Record hardware, OS, database, runtime, dataset size, request mix and test duration. Warm up and repeat runs. Report mean and p95. Never fabricate measurements.

## Workloads
| Level | Example concurrency | Observe |
|---|---:|---|
| Low | 10 | latency, throughput, errors |
| Medium | 50 | p95, connections, CPU/memory |
| High | 100 | saturation, errors, throughput plateau |
| Burst | 100 synchronized clients | 429/5xx, correctness, recovery |
Adjust levels to hardware. Keep request mix fixed.

## Metrics
- Throughput = completed requests / duration.
- Error rate = failed requests / total requests × 100%.
- Mean, p50 and p95 latency.
- CPU, memory and DB connections.
- Cache hit rate and hit/miss latency.
- Per-shard record/request counts and latency.
- Rate-limit accepted/rejected counts.
- IDs per second and collision count.
- Registration invariant violations, target zero.
- Moved-key fraction after topology changes.

## Baselines
Compare cache off/on, single database/sharded routing, modulo/consistent hashing, or unrestricted/rate-limited burst. Keep data and request mix identical.

## Registration correctness test
1. Set capacity N.
2. Send far more than N concurrent requests to one offering.
3. Verify enrollment never exceeds N and duplicates remain zero.
4. Count successful, waitlisted and rejected requests.
5. Compare with a naïve baseline.

## Shard scale test
Record per-shard counts, add a shard, measure movement and migration time, verify every record remains readable, then test removal. A ring update without data migration is not complete re-sharding.

## Failure test
Remove one app node or shard during a fixed workload. Record failures, detection time, recovery, p95 and duplicate writes. Report limitations if health checks or failover do not exist.

## Result table
| Design | Concurrency | Throughput req/s | Mean ms | p95 ms | Error % | CPU % | Memory MB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | | | | | | | |
| Proposed | | | | | | | |

Locust: https://docs.locust.io/en/2.20.2/what-is-locust.html