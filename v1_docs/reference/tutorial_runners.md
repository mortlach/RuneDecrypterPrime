# Tutorial Runners Reference

Status: staged V1 draft

Owners:

```text
tutorials/v1/run_pretty_print_release.py
tutorials/v1/run_pretty_print_output_review.py
tutorials/v1/run_all.py
```

## Pretty-Print Release Runner

Run:

```text
python tutorials/v1/run_pretty_print_release.py
```

This is the current V1 pretty-print review gate.

It owns:

- tutorial list
- per-tutorial minimum match thresholds
- compact console-output policy
- log output folder

The main constants are:

| Constant | Current role |
| --- | --- |
| `TITLE` | Runner title. |
| `SHOW_OUTPUT` | Whether every captured printout is echoed. |
| `STOP_ON_FIRST_FAILURE` | Whether to stop after the first failure. |
| `WRITE_LOGS` | Whether to write captured output logs. |
| `OUTPUT_DIR` | Repo-relative log folder. |
| `TAIL_LINES` | Failure tail size. |
| `TUTORIALS` | Selected tutorial files and thresholds. |

## Full Printout Review Runner

Run:

```text
python tutorials/v1/run_pretty_print_output_review.py
```

This runner imports the release runner, changes display policy constants, and
echoes all captured tutorial output. It is for human review of the tutorial
printouts.

## Manifest Runner

`tutorials/v1/run_all.py` still uses:

```text
tutorials/v1/tutorial_manifest_v1.json
```

Its policy is controlled by constants in the file.

## Current Alignment

The pretty-print runner list and `tutorial_manifest_v1.json` now describe the
same promoted tutorial files.

The runner owns the selected human-facing review set and thresholds. The
manifest owns classification metadata such as gate, asset profile, acceptance
kind, status, and notes.

## Target Alignment

The long-term target is:

- all working V1 tutorials live under `tutorials/v1/`
- every working tutorial has metadata
- the pretty-print runner selects the human-facing review set
- the manifest or successor metadata records gate, asset profile, acceptance,
  status, and notes
- public docs are easy to regenerate or check from the selected runner/metadata

This lets the tutorial set grow without turning the docs into a second manual
source of truth.

## Runner Policy

Public V1 tutorial runners should keep normal review behavior visible in the
runner file:

- constants near the top
- direct Python execution
- repo-relative output paths
- no separate config file for normal review
- no hidden shell-controlled tutorial selection
