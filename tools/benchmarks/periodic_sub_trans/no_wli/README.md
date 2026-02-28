# No-WLI Flavor

Runner for periodic substitution + transposition benchmarking without WLI features.

## Entrypoints

- `runner.py`: main no-WLI pipeline runner.
- `run_focus_p5_c1_c5.py`: focused launcher (`period=5`, `columns=1..5`).
- `run_focus_p5_c1_c5_a34.py`: focused launcher (`period=5`, `columns=1..5`, `A34->M34->B34`).

Examples:

- `python tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py`
- `python tools/benchmarks/periodic_sub_trans/no_wli/run_focus_p5_c1_c5.py`
- `python tools/benchmarks/periodic_sub_trans/no_wli/run_focus_p5_c1_c5_a34.py`

Campaign scope note:
- `no_wli` is currently internal tuning scope and is not part of public community v1.1 manifest schema.

## Operator Model (Hardcoded Knobs)

No-WLI launchers use hardcoded constants (not CLI args). Change knobs in file:

- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_focus_p5_c1_c5.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_focus_p5_c1_c5_a34.py`

Key selectors in `runner.py`:

- `NO_WLI_PIPELINE_PROFILE_ID`: scorer/solver schedule profile.
- `PIPELINE_RUN_MODE`: tier grid (`full`, `focus`, `smoke`, etc).
- `SCORER_IMPL`: Stage1/Stage2 scorer impl.
- `SCORER_STAGE3_IMPL_AVG_FULLTEXT`: Stage3 impl when objective is `avg.logp` with `avg_window_policy=full_text`.

## Scorer Routing

Stage routing is explicit:

- Stage1 and Stage2 use `SCORER_IMPL`.
- Stage3 uses `_effective_stage3_impl(...)`:
  - `avg.logp + avg_window_policy=full_text` -> `SCORER_STAGE3_IMPL_AVG_FULLTEXT`
  - else -> `SCORER_IMPL`

Verify in startup logs:

- `impl(stage1/2)=... impl(stage3)=...`
- `stage1=(...) stage2=(...) stage3=(...)`
- `setup: ecdf_guard=on ...` for avg full-text campaigns.

## Expected Failures (Fast Triage)

- `RuntimeError: [pipeline_no_wli] ECDF guard failed ...`
  - Cause: avg full-text scorer tried to initialize/access ECDF.
- `RuntimeError: CUDA backend requested but unavailable (...)`
  - Cause: `device=cuda` requested but CUDA backend not available.
- `ValueError: pct/energy objectives only support win=10 ...`
  - Cause: invalid `pct/energy` objective window.
- `ValueError: torch backend only supports avg.logp for raw objectives.`
  - Cause: raw scoring path requested with unsupported objective.

For broader scorer/backend policy, see `docs/setup/scorer_backend_selection.md`.
