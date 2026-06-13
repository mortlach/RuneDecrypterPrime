# Scorer Backend Selection

This note is for operators running benchmark pipelines and smoke checks.

## Controls

- `scorer_params.impl` (`"auto" | "numpy" | "torch" | "unified"`): scorer implementation request.
- `cipher.device` (`"cpu" | "cuda"`): device request used by backend selection.
- No-WLI runner hardcoded switches:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:70` (`SCORER_IMPL`)
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:71` (`SCORER_STAGE3_IMPL_AVG_FULLTEXT`)

## Build Selection Rules

`build_scorer(...)` (`src/rune_decrypter_prime/core/engine/builders.py`) resolves backends as:

1. If `impl=auto`:
   - `device=cuda` -> `impl=torch`
   - otherwise -> `impl=numpy`
2. If `device=cuda`, CUDA availability is checked.
3. Concrete scorer is then created from final `impl`.

Operationally, `impl=torch` can run on CPU or CUDA. A CUDA error is only raised when `device=cuda` is requested and unavailable.

## Objective/Backend Contract

- `pct.logp.win10` and `energy.logp.win10`:
  - supported on NumPy and Torch
  - `win` must be `10`
- `avg.logp.winK`:
  - supported on NumPy and Torch
  - for no-WLI stage3, `avg_window_policy=full_text` is supported and used in campaign profiles
- Torch scorer currently requires `se_mode=nose`.

## Expected Failure Modes

- CUDA unavailable when requested:
  - `RuntimeError: CUDA backend requested but unavailable (...)`
- Invalid `pct/energy` window:
  - `ValueError: pct/energy objectives only support win=10 in the current LM tables.`
- Invalid Torch raw objective:
  - `ValueError: torch backend only supports avg.logp for raw objectives.`
- No-WLI ECDF policy violation on avg full-text:
  - `RuntimeError: [pipeline_no_wli] ECDF guard failed ...`

## No-WLI Stage Routing

In `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`:

- Stage1/Stage2 use `SCORER_IMPL`.
- Stage3 uses `_effective_stage3_impl(...)`:
  - if objective is `avg.logp` with `avg_window_policy=full_text`, Stage3 impl is `SCORER_STAGE3_IMPL_AVG_FULLTEXT`
  - otherwise Stage3 impl follows `SCORER_IMPL`

Use startup logs to verify routing:

- `impl(stage1/2)=... impl(stage3)=...`
- `setup: ecdf_guard=on ...`
