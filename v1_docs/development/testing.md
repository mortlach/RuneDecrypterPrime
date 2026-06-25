# Testing

Status: staged V1 draft

This page is for contributors. The beginner path remains:

```text
python install.py
python tutorials/v1/run_tutorials.py
```

## Normal Test Command

From the repository root:

```text
python -m pytest
```

For focused work, run the smallest useful test file first:

```text
python -m pytest tests/api/test_display_summary_contract.py
```

Then broaden to the nearby package or contract tests that cover the behavior you
changed.

## Install Smoke Tests

The installer runs a compact smoke set after installation. That smoke set is
kept in `install.py`, not in this page, so the command remains simple:

```text
python install.py
```

If install fails, see [../troubleshooting.md](../troubleshooting.md).

## Tutorial Checks

For the pretty-print tutorial gate:

```text
python tutorials/v1/run_tutorials.py
```

For full printout review, set:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

Use this after changes to tutorial wording, rendering, report fields, rune
display, or output paths.

## Where Test Output Goes

Pytest session output is derived from the logging configuration in
`tests/conftest.py`.

Test artifacts are written under:

```text
output/tests/
```

This is generated output. Do not commit it.

## Choosing Tests

Use this rough map:

| Change area | Useful tests |
| --- | --- |
| RunSpec or source routing | `tests/api/test_runspec_contract.py`, `tests/api/test_runapi_runspec_routing.py` |
| Display summary | `tests/api/test_display_summary_contract.py`, `tests/api/test_printer_contract.py` |
| Solver reports | `tests/api/test_runapi_solver_report_visibility.py`, `tests/api/test_solver_report_truth_repro_contract.py` |
| Artifacts | `tests/api/test_artifact_agreement.py`, `tests/api/test_run_artifact_manifest.py` |
| Tutorial runner policy | `tests/contracts/test_v1_tutorial_runner_config_contract.py` |
| Tutorial reports | `tests/utils/test_tutorial_report.py`, `tests/utils/test_tutorial_session_report.py` |
| Rune encoding/display | `tests/utils/test_runeglish_encode_contract.py`, `tests/api/test_directional_plaintext_display.py` |
| LP labels and source refs | `tests/api/test_lp_label_source_ref.py`, `tests/api/test_lp_label_data_helpers.py` |

## Test Philosophy

Prefer a focused test that names the contract.

Good tests make drift obvious:

- direction is explicit
- truth/oracle use is visible
- generated reports stay JSON-safe
- paths are relative where public output is involved
- missing assets or unsupported lanes block clearly
- report-only diagnostics do not affect ranking

Do not hide a failure by weakening a test threshold unless the tutorial or
contract is explicitly reclassified.
