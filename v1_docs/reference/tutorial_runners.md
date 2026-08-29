# Tutorial Runner Reference

Status: staged V1 draft

## Public Runner

There is one public V1 tutorial runner:

```text
python tutorials/v1/run_tutorials.py
```

Retired runners have been deleted from the release tree and remain available in
Git history. The `tutorials/v1/` folder has one `run*.py` file.

## Editable Settings

Normal tutorial control is visible near the top of `run_tutorials.py`.

| Constant | Role |
| --- | --- |
| `RUN_SET` | Which tutorial set to run. |
| `CONSOLE_OUTPUT` | Compact status lines or full captured tutorial output. |
| `STOP_ON_FIRST_FAILURE` | Whether to stop after the first failed tutorial. |
| `WRITE_OUTPUT_LOGS` | Whether to write full per-tutorial logs. |
| `CLEAN_OUTPUT_LOGS` | Whether stale `.txt` logs are cleared before a new run. |
| `OUTPUT_DIR` | Repo-relative log folder. |
| `FAILURE_TAIL_LINES` | Failure-tail size for compact output. |
| `TUTORIALS` | Tutorial filenames, thresholds, acceptance kinds, and run sets. |

Run-set choices are enum values:

```python
RUN_SET = TutorialRunSet.RELEASE
```

The available sets are:

- `FAST`
- `RELEASE`
- `EXTENDED`
- `PARTIAL_RECOVERY`
- `OPTIONAL_LM3`
- `ALL_WORKING`

Console-output choices are also enum values:

```python
CONSOLE_OUTPUT = ConsoleOutput.COMPACT
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

Use `FULL` when reviewing the actual tutorial printouts by eye. The same runner
still writes logs under `output/tutorial_logs/`.

## Runner Policy

Public V1 tutorial runs should keep normal review behavior visible in the
runner file:

- constants near the top
- direct Python execution
- repo-relative output paths
- no separate config file for normal review
- no hidden shell-controlled tutorial selection
- no CLI switch matrix for beginner tutorial control
