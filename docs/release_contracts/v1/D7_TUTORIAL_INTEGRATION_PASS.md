# D7 tutorial integration pass

Branch: `prelease/v1.0.0_d7`

Status: integration pass validated locally for `full_v1`; not final D7 closure until release tutorial gate, full pytest after the latest runner-config fix, CI/equivalent proof, and regenerated review pack are available from the final branch head.

## Gate counts after this pass

Manifest counts by gate:

- `v1_smoke`: 4
- `v1_release`: 5
- `v1_extended`: 4
- `v1_showcase_near_solve`: 1
- `v1_slow_demo`: 1
- `optional_lm3`: 4
- `broken_contract_fix_needed`: 1
- `wrapper_script_fix_needed`: 1
- `remove_from_pure_release`: 0

Runner profile counts:

- `release`: 9 selected entries (`v1_smoke` + `v1_release`)
- `full_v1`: 14 selected entries (`v1_smoke` + `v1_release` + `v1_extended` + `v1_showcase_near_solve`)

## Promotion completed

Promoted to default release gate:

- `Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py`

Reason:

- exact real key-recovery tutorial under `lm2_baseline`
- `acceptance_kind = min_match_ratio`
- `min_match_ratio = 1.0`
- does not supply true key to solver
- uses public API via the ScheduledStreamLookup tutorial/session utility path

## Retained outside default release

Retained in `v1_extended`:

- `Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py`

Reason:

- exact under `lm2_baseline`, but retained outside default release to avoid making the default proof too heavy.

Retained in `v1_showcase_near_solve`:

- `Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py`

Reason:

- useful near-solve showcase
- exact recovery is not required under `lm2_baseline`
- acceptance is `near_solve_min_match` with `min_match_ratio = 0.9`

## Known-broken entries excluded from release/full_v1

- `Tutorial_PeriodicColumnar_Simple_P7_SubThenCol.py`
  - gate: `broken_contract_fix_needed`
  - current_status: `known_broken`
  - current issue: `make_true_periodic_columnar_key() got unexpected keyword argument 'order'`

- `Tutorial_ScheduledStreamLookup.py`
  - gate: `wrapper_script_fix_needed`
  - current_status: `known_broken`
  - direct real-solve scripts supersede it for release gates until the wrapper is fixed or removed

These are not silently skipped by release/full_v1 selection; they are manifest-classified and excluded by blocked gates/status.

## Output/report integration completed

ScheduledStreamLookup real tutorials now use:

- `return_solver_report=True`
- `TutorialReference.key_and_plaintext(...)`
- `TutorialStopPolicy(...)`
- `TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK`
- `print_tutorial_session_report(...)`

This means the release/extended/showcase ScheduledStreamLookup real tutorials emit unified tutorial/session reports with benchmark/truth-policy fields when they complete.

The tutorial runner now parses both older `Match ratio: ...` output and unified report `match_ratio : ...` output.

The tutorial runner keeps IDE-editable defaults but also accepts environment overrides for review/CI runs:

```bash
GATE_PROFILE=full_v1 python tutorials/v1/run_all.py
ASSET_PROFILE=lm3_extended python tutorials/v1/run_all.py
```

## Tests added/updated

- `tests/contracts/test_v1_tutorial_manifest_contract.py`
- `tests/contracts/test_v1_tutorial_runner_config_contract.py`
- `tests/tutorials/test_scheduled_stream_lookup_real_solve_tutorial.py`
- `tests/tutorials/test_scheduled_stream_lookup_tutorial.py`

These cover:

- manifest schema and required fields
- all `v1_release` entries exist on disk
- default release gate includes the exact ScheduledStreamLookup P13 supplied-sequence real solve
- P13 primes remains extended
- P13/P31 segmented remains showcase/near-solve
- known-broken entries are not selected by release/full_v1
- runner parses unified `match_ratio` output
- ScheduledStreamLookup real tutorials emit through the session benchmark report path
- gate/asset environment overrides are explicit and invalid boolean overrides fail loudly

## Validation evidence so far

User-reported local `full_v1` tutorial gate result after the ScheduledStreamLookup promotion and runner/test updates:

```text
RDP V1 tutorial runner | gate=full_v1 | asset_profile=lm2_baseline
Selected entries: 14
passed: 14
failed: 0
Process finished with exit code 0
```

Notable full_v1 outcomes:

- `Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py`: `PASS`, `match=1.000`, expected `>= 1.000`
- `Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py`: `PASS`, `match=1.000`, expected `>= 1.000`
- `Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py`: `NEAR_SOLVE_ACCEPTED`, `match=0.901`, expected `>= 0.900`

User-reported full pytest result after the ScheduledStreamLookup manifest-test updates, before the later runner-default contract fix:

```text
1177 passed, 41 skipped in 232.68s (0:03:52)
```

The skipped tests were expected environment/asset skips, including optional Torch/CUDA tests and optional LM3/LM4 asset tests.

## Required validation still pending

Run before claiming closure from the latest branch head:

```bash
GATE_PROFILE=release python tutorials/v1/run_all.py
python -m pytest -q -ra -p no:cacheprovider tests
```

Also confirm CI/equivalent proof after the latest runner-default contract fix, then regenerate the review pack from the final branch head.
