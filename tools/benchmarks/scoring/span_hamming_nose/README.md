# Span-Hamming NOSE Benchmark Suite

This folder contains the NOSE-only scorer benchmark suite used to calibrate and evaluate:

- `span_hamming` score behavior across text lengths
- separability vs synthetic generators
- optional char baseline correlations (`char1..char4`, `avg.logp`, full-text)

The suite is config-driven. Do not pass CLI arguments to change behavior.

## Files

- `bench_span_hamming_nose_suite.py`: main runner
- `schema.py`: corpus discovery, NOSE token validation, stride planner
- `report_span_hamming_nose_suite.py`: lightweight run report
- `merge_span_hamming_nose_shards.py`: deterministic shard merge utility

## Default Campaign (Fast Calibration Pass)

Current defaults in `bench_span_hamming_nose_suite.py` are tuned for practical runtime:

- `DIRECTIONS = ["ltr"]`
- `GENERATORS = ["REAL", "RAND_UNIGRAM", "SHUFFLE_UNIGRAM"]`
- reduced `MAX_WINDOWS_PER_BOOK_BY_L`
- `WRITE_SAMPLES_JSONL = False`
- `WRITE_DETAILED_SAMPLE_FIELDS = False` (scalar sample rows only)
- resume enabled
- shard strategy: deterministic by book hash

Use this pass first to get stable calibration quickly. Run RTL as a second pass.

## Run

Edit constants at the top of `bench_span_hamming_nose_suite.py`, then run:

```powershell
python tools/benchmarks/scoring/span_hamming_nose/bench_span_hamming_nose_suite.py
```

## Outputs

Each run writes to:

- `output/tools/benchmarks/scoring/span_hamming_nose_suite/<timestamp>__span_hamming_nose_suite.../`

Key files:

- `run_config.json`: resolved config + manifests
- `plan.csv`: planned REAL windows for this run/shard
- `book_manifest.csv`: all resolved books with `in_shard` flag
- `samples.csv`: per-sample rows appended continuously
- `completed_rows.csv`: completed REAL plan rows (resume anchor)
- `summary.csv`: aggregated metrics
- `calibration.json`: per-(direction,length) normalization refs
- `convergence.csv`: batch convergence deltas

When `WRITE_DETAILED_SAMPLE_FIELDS=False`, `samples.csv` contains compact scalar fields only.
Enable it for debug runs if you need per-length arrays in each sample row.

## Crash Safety / Resume

Resume is supported when reusing the same run directory.

Required settings:

- `RESUME_IF_RUN_DIR_EXISTS = True`
- `RUN_DIR_OVERRIDE = "<existing run dir>"`

Behavior:

- processed sample rows are already in `samples.csv`
- completed REAL rows are tracked in `completed_rows.csv`
- rerun skips completed rows and continues pending work

## Multi-Machine Sharding

Sharding is deterministic by **book id**:

- strategy: `book_hash_mod`
- each book belongs to exactly one shard

For `N` machines:

1. Set identical config and corpus on all machines.
2. Set `SHARD_COUNT = N` on all machines.
3. Set unique `SHARD_INDEX` per machine (`0..N-1`).
4. Keep separate run dirs per shard.

Validation metadata is written in `run_config.json`:

- `shard_count`, `shard_index`, `shard_strategy`
- `resolved_books` (pre-shard)
- `shard_books` + `shard_book_count` (post-shard)

## Combining Shards

Rule: combine at **sample level**, not by averaging shard summaries.

Recommended process:

1. Verify all shard `run_config.json` files match on:
   `global_seed`, `suite_version`, `length_buckets`, `generators`, `span_config`, `directions`.
2. Concatenate `samples.csv` across shards (single header).
3. Recompute `summary.csv` and `calibration.json` from merged samples.

Do not average per-shard `summary.csv`/`calibration.json` directly.

### Merge Script

Configure `tools/benchmarks/scoring/span_hamming_nose/merge_span_hamming_nose_shards.py`:

- `SHARD_RUN_DIRS` (explicit list), or
- `SHARD_PARENT_DIR` + optional `SHARD_GROUP_PREFIX` (auto-discover latest shard set)

Run:

```powershell
python tools/benchmarks/scoring/span_hamming_nose/merge_span_hamming_nose_shards.py
```

Merged output contains:

- `run_config.json`
- `plan.csv`
- `book_manifest.csv`
- `completed_rows.csv`
- `summary.csv`
- `calibration.json`
- optional `samples.csv` (only if `WRITE_MERGED_SAMPLES=True`)

## Gotchas

- Per-shard convergence is advisory, not global convergence.
- If you change planner/scoring constants, do not resume into an old run dir.
- `samples.csv` can be very large; JSONL is disabled by default for storage reasons.
- Run LTR and RTL separately for cleaner calibration/debugging.
