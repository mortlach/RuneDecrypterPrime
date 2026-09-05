# Outputs & Artefacts Guide

> Tracks: **Hands-on** sections explain where to find results after tutorials/tests; **Expert** sections describe how logging is initialised and validated.

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Locate `META.json`, `logs/app.jsonl`, `trace/`, and `artifacts/` for any run
Prereqs: Completed one tutorial or test run

## What This Page Covers
- Structure of the `output/` directory for tutorials/tests/tools.
- How to browse logs, traces, and artifacts.
- Required files (META, logging snapshots) for reproducibility.
- Links to troubleshooting and telemetry docs.

---

## Why It Matters
- **Hands-on** - everyone writes to the same predictable folders, making it easy to compare runs.
- **Expert** - output layout is part of the telemetry contract; CI expects logs and traces in canonical locations.
- **Mission** - output hygiene prevents personal path leakage and keeps determinism auditable.

---

## Canonical Tree
```text
output/
  tutorials/
    <timestamp>__tutorials__<label>__<git>__<unique-id>/
      META.json
      config/logging.json
      logs/app.jsonl
      trace/
      artifacts/
  tests/
    <timestamp>__tests__<label>__<git>__<unique-id>/
      META.json
      config/logging.json
      logs/app.jsonl
      trace/
      artifacts/tests/<pytest-nodeid>/
  telemetry/
    logs/run-*.jsonl   (optional mirror via telemetry.pipeline.dump_telemetry)
  share/
    <timestamp>__share__<label>/...  (symbol index, release bundles)
  release/
    ... (created by tools/repo_utils/make_release_src.py)
  solve/
    <puzzle_id_or_name>/<timestamp>/...
    <puzzle_id_or_name>/<solver_name>/<timestamp>/summary.json
```

This tree is relative to the selected output root. See [output locations](../development/output_locations.md)
for explicit configuration, inherited developer output and installed-package defaults.

---

## Hands-on Track - Reading Your Outputs
1. Run `python tutorials/v1/run_tutorials.py`.
2. Open `output/tutorial_logs/` to inspect the full output for each pretty tutorial.
3. Child tutorial artifacts live beneath their unique tutorial-run directory.
4. If you configured `RDP_OUTPUT_ROOT`, use that directory in place of `output/`.

---

## Expert Track - Logging & Validation
- **LoggingConfig** (`src/rdp/core/config/logging_config.py`) initialises the `output/<kind>/<run_id>/` folders used by tests and tooling.
- Tests (`tests/telemetry/test_schema_contract.py`) assume `META.json` includes repo/out roots, run IDs, git info, and pointers to logs/trace/artifacts.
- Tools (`tools/repo_utils/index_project_symbols.py`, `share_package.py`) write into `output/share/<timestamp>__share__<label>/`.
- Use `tools/ci/validate_outputs.py` to enforce that docs lint commands write into `output/tools/docs_lint/<...>/`.
- When adding scripts, call `io/run_logger.get_logger()` or `LoggingConfig` to guarantee they write inside `output/`.

**Verification checklist when touching logging:**
- `pytest tests/telemetry -q` (ensures schema + paths).
- `pytest tests/tests_docs -q` if you modify docs around outputs.
- Manual inspection: run `python tutorials/...` and confirm new files appear under the canonical tree.

---

## FAQ
- **Where do tests store per-case artifacts?** Under `output/tests/<run>/artifacts/tests/<pytest-nodeid>/` (see `tests/conftest.py`).
- **Can I change the base folder?** Yes by passing `out_root` to `LoggingConfig`, but tools/docs assume the default `output/` relative to repo root.
- **How do I share logs with someone else?** Zip the entire `output/<kind>/<run_id>/` folder; META.json + config snapshots ensure reproducibility.

---

## Related Docs
- `guides/telemetry.md` - describes the JSON payloads stored inside `logs/app.jsonl`.
- `guides/troubleshooting.md` - what to do if outputs are missing.
- `docs/tests_docs/tools.md` - how helper scripts (symbol index, release builder) populate the `output/share/` and `output/release/` trees.


## Related tests
- `tests/telemetry/test_schema_contract.py`
- `tests/telemetry/test_progress_events.py`
- `tests/pipeline/test_permutation_tracking.py`
- `tests/guardrails/test_suite_does_not_import_ui.py`
