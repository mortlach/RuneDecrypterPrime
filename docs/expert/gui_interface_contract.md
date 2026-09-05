# GUI interface contract

Status: V1 expert integrator guide

A GUI should use the typed public boundary:

```python
from rdp import api
```

Build an `api.RunSpec`, call `api.run`, and retain the resulting
`api.RunResult`. Do not import engine modules, instantiate runtime ciphers or
depend on human console wording.

## Display and sharing

```python
from pathlib import Path

summary = api.display.print_result(
    result,
    spec=run_spec,
    reference_plaintext=known_plaintext,
    options=api.display.SummaryOptions.standard(),
)
json_text = api.display.render_summary(
    summary,
    output_format=api.display.PrintFormat.JSON,
)
relative_path = api.display.write_summary_artifact(
    summary,
    run_dir=Path("output/run"),
)
```

The standard JSON sidecar is
`artifacts/rdp_display_summary.json`. Returned display paths are run-relative;
absolute machine paths remain internal to the writer.

## GUI-owned inputs

A GUI should collect typed equivalents of:

- one raw-text, rune-index or source-reference input;
- cipher and compatible key-space specs;
- solver and scoring specs;
- direction, device, telemetry and optional permutation/interruptor policy;
- an optional logging config for durable output.

Serialized GUI state may use `from_dict` parsers at its loading boundary. Once
loaded, the GUI should hold typed objects rather than mutable parameter maps.

RDP V1 does not promise a machine-readable example catalogue. The human
catalogue is `tutorials/v1/README.md`; the source-checkout runner is
`tutorials/v1/run_tutorials.py`. A GUI should own its navigation metadata and
use the public API for execution rather than parsing either file. It should show
reported stop status, blocked capabilities, oracle use, partial-recovery policy
and artefact status explicitly.
