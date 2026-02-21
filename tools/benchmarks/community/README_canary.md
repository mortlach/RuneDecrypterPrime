# Canary Run (v1.1)

The canary run is a short end-to-end smoke test intended to catch problems early.

## When to run canary
Run canary after setup/preflight passes and before running a full shard.

## What canary contains
- 6–12 jobs
- spans both orders
- includes at least one small column case (e.g. c=3)
- one profile (baseline)
- 1 replicate per job

## What to do if canary fails
Stop. Share:
- setup_report.json + setup.log
- preflight_report.json + preflight.log
- run.log + results.jsonl (partial)
