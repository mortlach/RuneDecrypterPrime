# LoggingConfig parameters

`RunSpec.logging` defaults to `None`. Supplying `LoggingConfig` enables the run
output route.

| Parameter | Type | Default | Notes / constraint |
| --- | --- | --- | --- |
| `output_root` | `Path | None` | `None` | Explicit output root. |
| `run_category` | `str` | `"run"` | Non-empty category name. |
| `label` | `str | None` | `None` | Optional run label. |
| `run_directory` | `Path | None` | `None` | Optional exact run directory. |
| `redact_identity` | `bool` | `False` | Explicit identity redaction. |
| `portable_output` | `bool` | `True` | Portable metadata. Also causes identity to be redacted. |
| `write_solver_report` | `bool` | `False` | Write the solver report artifact. |
| `write_display_summary` | `bool` | `False` | Write the display summary artifact. |
| `write_artifact_manifest` | `bool` | `False` | Write the artifact manifest. |

All boolean fields require actual booleans. `output_root` and `run_directory`
use `Path` objects when supplied.

`LoggingConfig.from_dict(values)` accepts only these fields and converts string
paths for `output_root` and `run_directory` to `Path` objects.

Live progress is separate from durable logging. Supply a one-argument
`progress_callback` to `api.run(...)`; `LoggingConfig` has no presentation or
event-log switches.

For practical use, see [Outputs](../../guides/outputs.md).
