# Merge Issue Log (2026-03-08)

## 1) Absolute machine paths in tracked script

- File: `tools/benchmarks/scoring/word_ngrams/build_word_ngrams_lp_sqlite_v1.py`
- Symptom:
  - tidy sweep failed on absolute path constants
- Fix:
  - moved defaults to `REPO_ROOT / ...` repo-relative paths
- Guard:
  - keep `tests/meta/test_repo_tidy_sweep.py::test_repo_has_no_absolute_machine_paths` in merge gate

## 2) No-WLI runtime binding gaps

- Symptom A:
  - `KeyError: '_commit_iteration_outputs_bridge_external'`
- Symptom B:
  - `KeyError: 'write_pipeline_snapshot_files'`
- Fixes:
  - wired `_commit_iteration_outputs_bridge_external` in
    `tools/benchmarks/periodic_sub_trans/no_wli/runner_bindings.py`
  - ensured `write_pipeline_snapshot_files` import in
    `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- Guard:
  - `tests/tools/test_no_wli_runner_bindings_commit_bridge.py`

## 3) Missing span assets crashed default runner startup

- Symptom:
  - `FileNotFoundError` for
    `assets/scoring/span_hamming_nose_assets_v1/combined_calibration.json`
- Root cause:
  - adaptive focus mode forced `SCORING_EXPERIMENT_PROFILE="c_min_late"` without optional asset pack present
- Fixes:
  - fallback to `SCORING_EXPERIMENT_PROFILE="off"` when span assets are missing in
    `tools/benchmarks/periodic_sub_trans/no_wli/runner_bindings.py`
  - prevent forced phase switch to `c_min_late` when profile is `off` in
    `tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py`
- Guard:
  - `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py::test_no_wli_missing_span_assets_fallbacks_scoring_experiment_to_off`

## 4) Synced packed assets carried absolute provenance paths

- Files:
  - `assets_packed/span_hamming_nose_assets_v1_ltr/combined_calibration.json`
  - `assets_packed/span_hamming_nose_assets_v1_ltr/metrics.json`
  - `assets_packed/span_hamming_nose_assets_v1_rtl/combined_calibration.json`
  - `assets_packed/span_hamming_nose_assets_v1_rtl/metrics.json`
- Symptom:
  - tidy sweep failed on absolute `source_run_dir` values inside synced JSON metadata
- Fix:
  - sanitized `source_run_dir` to repo-relative `output\\...` paths
- Guard:
  - `tests/meta/test_repo_tidy_sweep.py::test_repo_has_no_absolute_machine_paths`

## 5) Validation run missed word-ngram telemetry because config was off

- Symptom:
  - solved run completed, but `word_ngram_report`, `stage2_topk_word_ngram_report`, and
    `stage3_topk_word_ngram_report` were empty
- Root cause:
  - `run_config.json` had `stage3.word_ngram_report.enabled=false` and empty sqlite path
- Fix:
  - no-WLI runner defaults now auto-enable report-only word-ngram telemetry when a local
    SQLite asset is discoverable, and auto-fill the path
  - file: `tools/benchmarks/periodic_sub_trans/no_wli/runner_defaults.py`
- Guard:
  - `tests/tools/test_no_wli_runner_defaults_word_ngram.py`
