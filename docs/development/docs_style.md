# Documentation style

Status: V1 cleanup policy

## Tutorial runner policy

Public V1 tutorial runners must not require or advertise RDP environment
variables. Normal users should run a Python file directly.

Allowed:

- clear constants in the runner file
- a small number of separate runner files for distinct review gates
- tutorial manifest data used by tests and release gates

Avoid:

- `RDP_TUTORIAL_*` environment variables
- `PYTHONPATH` instructions
- shell-specific setup
- CLI-heavy tutorial control
- separate config files unless the config is genuinely reused by more than one
  runner

The normal V1 tutorial command is:

```text
python tutorials/v1/run_pretty_print_release.py
```

Use `python tutorials/v1/run_pretty_print_output_review.py` when reviewing the
full human-facing tutorial printouts.
