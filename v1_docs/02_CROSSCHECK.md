# V1 documentation cross-check

Status: historical audit ledger, updated to point at the implemented AN3 public
field names. Recorded test counts below remain historical evidence.

This page records checks made while drafting `v1_docs/`. It should be updated
whenever the staged docs claim a current runner list, report field, artifact
path, or tutorial policy.

## Checks Run

The staged docs were checked against the current clean release tree with small
read-only scripts and text scans.

Checked:

- pretty-print tutorial runner list and thresholds
- staged tutorial table
- tutorial manifest schema and entries
- `RunSpec` fields
- `RunResult` fields
- `SolverReport` fields
- `ScorerReport` fields
- artifact kind/path/classification enums
- LP `SourceReferenceInput` source kinds
- staged docs setup-pattern hygiene
- staged docs whitespace hygiene

## Confirmed Matches

### Pretty-Print Tutorial List

`v1_docs/tutorials.md` matches `tutorials/v1/run_tutorials.py`.

Confirmed:

- runner tutorial count: 21
- staged docs tutorial count: 21
- no missing tutorial file names in `v1_docs/tutorials.md`
- no extra tutorial file names in `v1_docs/tutorials.md`
- no threshold mismatches

### Report And Input Fields

`v1_docs/reference/run_spec.md` and `v1_docs/reference/reports.md` match the
current field lists:

```text
RunSpec:
problem_input, cipher, key_space, solver, scoring, initial_keys, logging,
word_length_policy, text_direction, compute_device, telemetry_enabled,
text_permutation, interruptors

RunResult:
plaintext, plaintext_text, key, score, status, solver_report, scorer_report,
configuration, reproducibility, oracle, telemetry, artifacts

SolverReport:
solver, parameters, requested_seed, effective_seed, status, best_key,
best_score, evaluations, steps, tokens_processed, wall_time_seconds,
decrypt_time_seconds, score_time_seconds, details

ScorerReport:
objective, score, raw_score, telemetry, metrics, time_seconds, capabilities,
details
```

### Artifact Paths

`v1_docs/reference/artifacts.md` matches the current artifact enums:

```text
META.json
config/logging.json
artifacts/solver_report.json
artifacts/rdp_display_summary.json
artifacts/run_artifacts_manifest.json
```

Artifact kinds:

```text
run_meta
logging_config
solver_report
rdp_display_summary
run_artifacts_manifest
```

Classifications:

```text
candidate
not_candidate
needs_review
```

### LP Source Kinds

`v1_docs/reference/run_spec.md` and `v1_docs/lp_examples.md` match the current
LP source kinds:

```text
liber_primus.label
liber_primus.locator
liber_primus.partition
```

## Tutorial Manifest Alignment

The current pretty-print release runner owns this selected review list:

```text
tutorials/v1/run_tutorials.py
```

It selects 21 promoted tutorial files.

The current tutorial manifest is:

```text
tutorials/v1/tutorial_manifest_v1.json
```

It now lists the same 21 promoted tutorial files. Older replaced files were
were removed from the release tree after the complete retired tutorial tree was
owner-approved for deletion. Git history preserves the retired material.

This is now documented in:

- `tutorials_as_evidence.md`
- `reference/tutorial_runners.md`

Target:

```text
All working V1 tutorials should eventually live under tutorials/v1/ with clear
metadata, even when they are not selected for the beginner release gate.
```

Extensibility requirement:

```text
Adding a new working tutorial should require a small, obvious set of updates:
tutorial file, runner selection if selected, metadata, docs table if public,
and a focused alignment test.
```

## Hygiene Results

The staged docs passed:

```text
git diff --check -- v1_docs
```

The staged docs also passed scans for stale beginner-path setup/control
patterns that should not be introduced here. The only intentional exception is
normal contributor `python -m pytest` usage in contributor/testing docs.

The staged docs are ASCII-only.

Local Markdown links inside `v1_docs/` were checked.

Result:

```text
missing_links=0
```

## Focused Contract Tests

Focused tests were run against the code surfaces described by these staged docs.

Commands:

```text
python -m pytest -q tests/contracts/test_v1_tutorial_runner_config_contract.py tests/api/test_display_summary_contract.py tests/api/test_artifact_agreement.py tests/api/test_run_artifact_manifest.py
python -m pytest -q tests/api/test_runspec_contract.py tests/api/test_v1_public_contract.py tests/api/test_solver_report_truth_repro_contract.py tests/scoring/test_scorer_report_lane_sections.py
python -m pytest -q tests/utils/test_runeglish_encode_contract.py tests/api/test_directional_plaintext_display.py tests/utils/test_tutorial_report.py tests/utils/test_tutorial_session_report.py
```

Result:

```text
127 passed
```

After the tutorial rename and old-file move, this focused set was run again:

```text
python -m pytest -q tests/contracts/test_v1_tutorial_runner_config_contract.py tests/contracts/test_v1_tutorial_manifest_contract.py tests/tutorials/test_scheduled_stream_lookup_real_solve_tutorial.py tests/tutorials/test_scheduled_stream_lookup_tutorial.py tests/api/test_directional_plaintext_display.py tests/utils/test_runeglish_encode_contract.py tests/api/test_display_summary_contract.py
```

Result:

```text
34 passed
```

## Next Cross-Checks

Before replacing old public docs:

- run `run_tutorials.py` once on the target machine
- run `run_tutorials.py` with `CONSOLE_OUTPUT = ConsoleOutput.FULL` when ready to review wording
- plan the easy-update path for tutorial number 22 and beyond
- check old `docs/INDEX.md` replacement or redirect policy
- check whether `docs/README.md` should point to `v1_docs/` during staging
- decide which solved LP workbooks are public tutorials versus advanced examples
