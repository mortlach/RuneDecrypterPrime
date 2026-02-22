# Requirements Targets

Targeted dependency lists for the cross-platform bootstrap flow live here.

Run with:

```bash
python install.py --target runner
```

Available targets:

- `runner`: contributor node that runs shard jobs.
- `organiser`: validator/combine/aggregate node.
- `dev`: full local development stack.
- `ci-smoke`: lightweight CI smoke stack.

Notes:

- Files are intentionally explicit and deterministic.
- Update these files whenever benchmark tooling dependencies change.
- `tools/benchmarks/community/bootstrap.py` selects one target file by default.
