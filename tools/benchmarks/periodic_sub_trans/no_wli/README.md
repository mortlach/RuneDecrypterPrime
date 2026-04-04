# No-WLI Flavor

Runner for periodic substitution + transposition benchmarking without WLI features.

## Entrypoints

- `runner.py`: main no-WLI pipeline runner.
- `runs/run_focus_p5_c1_c5.py`: focused launcher (`period=5`, `columns=1..5`).
- `runs/run_focus_p5_c1_c5_a34.py`: focused launcher (`period=5`, `columns=1..5`, `A34->M34->B34`).
- `run_fixture_matrix.py`: internal fixture-matrix launcher using community-style fixture config (no public campaign schema changes).

Examples:

- `python tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py`
- `python tools/benchmarks/periodic_sub_trans/no_wli/runs/run_focus_p5_c1_c5.py`
- `python tools/benchmarks/periodic_sub_trans/no_wli/runs/run_focus_p5_c1_c5_a34.py`
- `python tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`

Campaign scope note:
- `no_wli` is currently internal tuning scope and is not part of public community v1.1 manifest schema.

Legacy snapshots:
- Historical runner snapshots are kept under `tools/benchmarks/periodic_sub_trans/no_wli/old/`.
- The stale nested package-local output archive was removed because its
  mirrored `tools/benchmarks/...` subpaths caused Windows path-length failures
  in Git tooling.
- Active generated artifacts belong under
  `output/tools/benchmarks/periodic_sub_trans/no_wli/`; package-local
  `tools/benchmarks/periodic_sub_trans/no_wli/output/` and
  `tools/benchmarks/periodic_sub_trans/no_wli/old/output_legacy_nested/` are
  intentionally ignored.
- Active implementation surface is split into:
  - top-level `no_wli/*.py` solver/runtime modules
  - `no_wli/analysis/*.py` audit/export/profile tooling
  - `no_wli/runs/*.py` standalone launchers/harnesses

## Operator Model (Hardcoded Knobs)

No-WLI launchers use hardcoded constants (not CLI args). Change knobs in file:

- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runs/run_focus_p5_c1_c5.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runs/run_focus_p5_c1_c5_a34.py`

Key selectors in `runner.py`:

- `NO_WLI_PIPELINE_PROFILE_ID`: scorer/solver schedule profile.
- `PIPELINE_RUN_MODE`: tier grid (`full`, `focus`, `smoke`, etc).
- `SCORER_IMPL`: Stage1/Stage2 scorer impl.
- `SCORER_STAGE3_IMPL_AVG_FULLTEXT`: Stage3 impl when objective is `avg.logp` with `avg_window_policy=full_text`.
- `SCORING_EXPERIMENT_PROFILE`: Stage3 scoring experiment (`off | a_baseline | b_min | c_min_late`).

Run modes are intent-driven contracts:

- `scan_fast_v1`: triage only; Stage-3 may be skipped; finishes quickly; does not promise solves.
- `adaptive_scan_v1`: triage-with-effort; can spend up to Stage-2 cap trying to earn Stage-3; Stage-3 may still be skipped.
- `adaptive_focus_v1`: solve-oriented; Stage-3 is always attempted; no scan guardrails skip Stage-3.
- `adaptive_fixture_v1`: internal solve-oriented mode for external fixture grids; keeps caller-provided tiers/seeds/offsets and still forces Stage-3 attempt (no scan skip path).
- `scan_p5_p7_c1357`: legacy alias -> `adaptive_scan_v1`.

## Internal Fixture Matrix Mode

`run_fixture_matrix.py` is for internal no-WLI sweeps on community fixture files while keeping no-WLI out of public community manifest/order schemas.

Edit hardcoded knobs in:

- `CAMPAIGN_CONFIG_PATH`
- `RUN_MODE` (recommended: `adaptive_fixture_v1`)
- `SCHEDULE_COVERAGE_MODE` (`minimal_avg_ids`, `minimal_all_ids`, `cartesian_all`, `explicit`)
- `SCORING_EXPERIMENT_PROFILES` (use `c_min_late` for span-hamming enabled phase-B path)
- period/column overrides and run seeds
- `FIXTURE_LENGTH_OVERRIDE` (set `1000` for shorter overnight runs)
- `MAX_WALLCLOCK_SECONDS` (optional cap; default `None` means no hard time limit)
- `REQUIRE_NO_WIN10_OBJECTIVES` (`True` enforces the no-win10 golden rule at launch build time)
- `REQUIRE_FULL_TEXT_EFFECTIVE` (`True` enforces `avg_window_policy=full_text` on all stages)
- `DISABLE_STAGE3_SPAN_BASIN_K_SWEEP` / `STAGE3_SPAN_BASIN_K_SWEEP_VALUES` for basin-judge K sweep control
- `RESUME_SKIP_COMPLETED` (`True` skips jobs already checkpointed as completed)

Interruption safety:
- Progress is written after each completed job to:
  - `fixture_matrix_run_state_latest.json`
  - `fixture_matrix_run_events_latest.jsonl`
- Re-running the launcher with `RESUME_SKIP_COMPLETED=True` continues from remaining jobs.

Current overnight defaults in `run_fixture_matrix.py` are aligned to the best avg/full_text no-WLI path:
- profile: `no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1`
- schedule: `A_char2_avg_fulltext -> M_char4_avg_fulltext -> B_char4_avg_fulltext`
- run mode: `adaptive_fixture_v1` (external tier grid preserved, adaptive phase-A/phase-B scoring path enabled)
- scoring experiment: `c_min_late`
- period ladder: `p5,p7,p9,p11,p13` with progressively wider odd-column sets

Use `DRY_RUN_ONLY` to control execution:
- `True`: plan-only (no runner execution)
- `False`: execute jobs

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

## Span-Hamming Workflow (Stage3)

No-WLI uses a fixed three-stage objective flow:

- Stage1: `avg.logp full_text` with char2 (broad basin search).
- Stage2: `avg.logp full_text` with char4 (candidate ranking/promote pool).
- Stage3: `pct.logp.win10` char4 refine, optionally with calibrated span-hamming.

`SCORING_EXPERIMENT_PROFILE` only changes Stage3:

- `a_baseline`: char4 pct only (no span).
- `b_min`: char4 pct + calibrated span, combine mode `min`.
- `c_min_late`: same as `b_min` plus `span_hamming_char_pct_min` gate.

In `c_min_late`, candidates below the char-pct gate skip span backend work and fall back to the base char score (`char_only` gate policy). This keeps span active for strong candidates while avoiding wasted compute and score-floor collapse on weak candidates.

For `adaptive_focus_v1` with Stage-3 two-phase enabled, Stage-3 uses scorer switching:

- Phase A experiment: `a_baseline` (char-only, cheap).
- Phase B experiment: `c_min_late` (selective span).
- Phase-B char gate is derived per tier from oracle score: `clip(oracle_pct - 0.10, 0.30, 0.45)`.

## Scan Policy

For `adaptive_scan_v1` (and legacy alias `scan_p5_p7_c1357`), the runner forces `SCORING_EXPERIMENT_PROFILE="c_min_late"` to keep Stage-3 selective.

Scan also applies two guardrails before Stage-3:

- Stage-2 continuation (`SCAN_STAGE2_CONTINUE_TO_GATE`): Stage-2 keeps expanding candidate work until either:
  - `best_match_ratio >= SCAN_STAGE3_GATE_LOW_MATCH`, or
  - `SCAN_STAGE2_CONTINUE_CAP_SECONDS` is reached.
- Per-tier wall-clock cap (`SCAN_TIER_TIME_CAP_SECONDS`): if elapsed time already exceeds cap, Stage-3 is skipped.
- Three-level Stage-3 policy (scan only):
  - `best_match_ratio < SCAN_STAGE3_GATE_LOW_MATCH` -> skip Stage-3.
  - `SCAN_STAGE3_GATE_LOW_MATCH <= best_match_ratio < SCAN_STAGE3_GATE_HIGH_MATCH` -> run Phase-A only (Phase-B forced skip).
  - `best_match_ratio >= SCAN_STAGE3_GATE_HIGH_MATCH` -> allow normal Phase-B gate/escalation.

`SCAN_STAGE3_MIN_STAGE2_MATCH` is kept as a legacy alias for `SCAN_STAGE3_GATE_LOW_MATCH`.

These are benchmark throughput controls for broad sweeps; focused runs should use tighter settings.

Check logs:

- `setup: scoring_experiment=...`
- `stage3=(B_char4_pct_...)`
- `stage3-stop ... entry_score_source=...`

## Outcome Codes

Per-tier rows now include `outcome_code` and `summary.json` reports `outcome_counts` per tier.

Standard codes:

- `skipped_proven`
- `solved`
- `weak_stage2`
- `time_cap`
- `stage2_cap`
- `stalled_stage3`
- `crash`
- `unsolved`

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

## Stage Trace Quick Read

Use `stage_engine_trace.jsonl` as the single ordered decision trace for each run.

Key event types:

- `stage_start`: stage boundary and aux-objective contract fields.
- `stage_end`: stage boundary output and per-stage counters.
- `error`: stage exception payload (if raised).
- `span_budget_plan`: budget-derived span call plan (`calls_affordable`).
- `span_eval_selection_plan`: planned span eval subset per scope (`candidate`, `topk`, `basin_rep`).
- `span_shadow_counterfactual`: optional shadow callback payload for "what span would have done".

Fields to watch first:

- `stage_id`, `stage_index`, `event`
- `in_pool_size`, `out_pool_size`
- `span_calls_total`, `span_calls_active`, `span_calls_rejected_or_gated`
- `span_seconds_total`, `span_active_rate`, `span_active_rate_source`
- `aux_decision_influence` (must remain `false` for shadow-only scaffolding)

Stage rows (`stages.csv`) remain the per-stage summary table; `stage_engine_trace.jsonl` is the event-level timeline.
