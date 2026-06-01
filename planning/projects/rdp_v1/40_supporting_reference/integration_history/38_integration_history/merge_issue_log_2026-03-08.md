# Merge Issue Log (2026-03-08)

## 2026-03-08 - Absolute machine paths in tracked script

- Source: `tests/meta/test_repo_tidy_sweep.py::test_repo_has_no_absolute_machine_paths`
- Offender file: `tools/benchmarks/scoring/word_ngrams/build_word_ngrams_lp_sqlite_v1.py`
- Symptom:
  - `NGRAM_SOURCE_ROOT = Path(r"C:\path\to\google_ngrams_Version-20200217")`
  - `OUTPUT_SQLITE = Path(r"C:\path\to\assets\word_ngrams_lp_v1.sqlite")`
- Fix applied:
  - Switched to repo-root-relative constants:
    - `NGRAM_SOURCE_ROOT = REPO_ROOT / "data" / "scoring" / "google_ngrams_Version-20200217"`
    - `OUTPUT_SQLITE = REPO_ROOT / "assets" / "scoring" / "word_ngrams" / "word_ngrams_lp_v1.sqlite"`
- Prevention rule:
  - No hardcoded machine absolute paths in tracked code.
  - All default script paths must be repo-relative (prefer `REPO_ROOT / ...` in internal scripts).
  - Keep `test_repo_tidy_sweep` in pre-merge validation gate.

## 2026-03-08 - Runtime wiring regressions in modular no-WLI runner

- Symptom 1:
  - `KeyError: '_commit_iteration_outputs_bridge_external'`
- Fix:
  - Installed binding in `tools/benchmarks/periodic_sub_trans/no_wli/runner_bindings.py`.

- Symptom 2:
  - `KeyError: 'write_pipeline_snapshot_files'`
- Fix:
  - Imported `write_pipeline_snapshot_files` in `tools/benchmarks/periodic_sub_trans/no_wli/runner.py` to populate runtime state.

- Prevention rule:
  - Add/keep a lightweight runner binding smoke test that asserts required runtime keys are present.
  - Keep one bounded no-WLI runtime smoke run in merge closeout before long campaigns.

## 2026-03-08 - Missing span assets blocked default runner startup

- Symptom:
  - Running `tools/benchmarks/periodic_sub_trans/no_wli/runner.py` failed at startup with:
    - `FileNotFoundError: Missing combined_calibration.json for span experiment: assets/scoring/span_hamming_nose_assets_v1/combined_calibration.json`
- Root cause:
  - Adaptive focus mode forces `SCORING_EXPERIMENT_PROFILE="c_min_late"` by default.
  - Local workspace may not include optional span calibration assets.
- Fix applied:
  - In `tools/benchmarks/periodic_sub_trans/no_wli/runner_bindings.py`:
    - catch `FileNotFoundError` for `b_min|c_min_late`, emit warning, and fallback to `SCORING_EXPERIMENT_PROFILE="off"` for this run.
  - In `tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py`:
    - only force phase A/B (`a_baseline`/`c_min_late`) when scoring experiment profile is not `off`.
  - Added regression test:
    - `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py::test_no_wli_missing_span_assets_fallbacks_scoring_experiment_to_off`
- Prevention rule:
  - Treat span calibration assets as optional for baseline runner startup.
  - Keep fallback behavior under test so missing optional asset packs do not hard-stop default benchmarking.
