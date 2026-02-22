# Community Benchmark Branch Guide

This file is retained for compatibility, but the canonical benchmark workflow is now:

- `python install.py --target runner`
- `tools/benchmarks/community/README.md`

## Important

Legacy "autoskip proven" branch behavior is not the campaign standard for v1.1.
Campaign mode requires:

1. Resume-only skips (explicitly logged).
2. Deterministic manifests/shards from tracked config.
3. CPU-only compliance fields in results.
4. Shareable `run_bundle` outputs validated before combining.

Use the community scripts in this folder (`generate_manifest.py`, `shard_manifest.py`,
`run_shard.py`, `validate_run_bundle.py`, `combine_results.py`, `aggregate_results.py`)
as the source of truth.
