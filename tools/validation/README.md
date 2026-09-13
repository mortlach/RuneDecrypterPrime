# Validation launchers

This folder contains terminal launchers for repository validation. The Python
selection and evidence implementation remains in `tools/run_validation.py` so
existing imports and automation continue to work.

`run_full_validation.ps1` launches the configured `all` selection in the active
source-install environment. It mirrors UTF-8 output to the visible terminal and
to `full_validation_console.log`.

Before launching, set `RDP_VALIDATION_OUTPUT_ROOT` to an absolute folder outside
the repository. The Python runner writes individual job logs, JUnit output,
summaries, and artifacts beneath that folder's `runner_output/validation/`
directory. The PowerShell launcher waits for Enter after completion so the
terminal remains available for review.

The launcher accepts no command-line arguments. Selection changes belong in the
small configuration block at the top of `tools/run_validation.py`.
