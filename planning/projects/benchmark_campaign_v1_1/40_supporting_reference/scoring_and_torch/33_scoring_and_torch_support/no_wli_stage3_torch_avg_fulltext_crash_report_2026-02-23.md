# no-WLI Stage-3 Torch AVG FULL_TEXT Crash Report (2026-02-23)

Status: Active incident reference.

Gating/closure tracking is maintained in:

- `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`

## Incident Summary

- Symptom: process exits with Windows access violation code `0xC0000005` (`-1073741819`) during no-WLI benchmark runs.
- Context: no-WLI Stage-3 switched to `avg.logp.win20` with `avg_window_policy=full_text`.
- Impact: long benchmark runs terminate without Python traceback; run progress is lost unless resumed from artifacts.

## What Was Observed

From runner logs:
- Stage-1 and Stage-2 continue to run normally under `pct.logp.win10` and Torch.
- Stage-3 enters AVG full-text path and logs lines like:
  - `model=avg.logp.win20 (char34,...)`
- Process later terminates with:
  - `Process finished with exit code -1073741819 (0xC0000005)`

This strongly indicates a native crash path (C/C++/Torch runtime), not a Python exception.

## Evidence and Suspects

### 1) Newly exercised Stage-3 objective path
- `tools/benchmarks/config/no_wli_pipeline_profiles.py:242`
- `tools/benchmarks/config/no_wli_pipeline_profiles.py:255`
- `tools/benchmarks/config/no_wli_pipeline_profiles.py:257`

Why suspect:
- Introduced `no_wli_a1_m12_b34_stage3avg_fulltext_v1` with:
  - `objective="avg.logp.win20"`
  - `avg_window_policy="full_text"`

### 2) no-WLI runner default now selects that profile
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:63`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:727`

Why suspect:
- This made the new Stage-3 path active in normal runs.

### 3) Torch scorer full-text AVG path is new and native-heavy
- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:856` (`_score_raw_logp_full_text`)
- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:89` (`_xxh64_u32words_cpu`)
- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:128` (`_xxh64_u32words_device`)
- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:1120` (`_score_raw_logp_win` dispatch)

Why suspect:
- Crash appears only once Stage-3 AVG full-text path is active.
- Exit mode is native access violation.
- Path includes low-level hashing/probing operations on packed n-grams.

## Current Mitigation (Applied)

Runner-level safety guard is in place:
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:70`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:313`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:539`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:735`

Behavior:
- Stage-1/2 keep `impl=torch`.
- Stage-3 AVG full-text is forced to `impl=numpy` to avoid the crashing native path.

## Repro Harness and Test Scaffolding

Added minimal repro script:
- `tools/benchmarks/periodic_sub_trans/no_wli/repro_stage3_torch_avg_fulltext_access_violation.py`

Added manual pytest wrapper (off by default):
- `tests/tools/test_no_wli_stage3_torch_avg_fulltext_crash_repro.py`
- gate constant: `RUN_CRASH_REPRO = False`
- expected crash code set includes `-1073741819`.

## Proposed Debug Plan (Root Cause)

1. Reproduce consistently with the dedicated repro script.
2. Isolate within Torch full-text path:
   - temporarily force full-text path to use safer CPU-only hash/probe branch.
   - run `char_n3` only, then `char_n4` only, then combined.
3. Add temporary internal diagnostics in `torch_rune_scorer`:
   - emit per-model token shape/type before hashing/probing.
   - emit probe-loop bounds/sentinel checks.
4. Compare against NumPy full-text output for same candidate batch:
   - detect divergence before crash point.
5. Implement permanent Torch-side fix only after deterministic repro confirms root cause.

## Proposed Permanent Fix Options

1. Preferred: fix Torch AVG full-text hashing/probe path and restore Stage-3 Torch.
2. Fallback: keep Stage-3 AVG full-text on NumPy permanently for no-WLI flavor if Torch path remains unstable.

## Acceptance Criteria for Closure

1. Repro script completes repeatedly on Windows without `0xC0000005`.
2. Manual repro pytest no longer observes access-violation on enabled runs.
3. no-WLI long run completes full tier set with Stage-3 Torch AVG full-text enabled.
4. NumPy/Torch AVG full-text parity remains within existing tolerances.
