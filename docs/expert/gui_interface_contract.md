# GUI interface contract

Status: expert integrator guide

This page describes the practical interface a GUI or overlay should use.

It is intentionally small. It describes the stable concepts, not every internal
Python class.

## Input surfaces

A GUI should prefer these inputs:

```text
tutorials/v1/tutorial_manifest_v1.json
tutorials/v1/run_all.py
RDP_TUTORIAL_GATE_PROFILE
RDP_TUTORIAL_ASSET_PROFILE
RDP_TUTORIAL_ECHO_OUTPUT
```

For user choices, expose:

```text
tutorial_id
gate_profile
asset_profile
seed, where supported
source label, where supported
output folder
```

## Standard display/share surface

The preferred structured display surface is the API standard summary:

```python
from rune_decrypter_prime.api import (
    RdpDisplayOptions,
    build_rdp_summary,
    print_rdp_summary,
    write_rdp_summary_json,
)

summary = build_rdp_summary(
    result,
    spec=run_spec,  # preferred when available
    reference_plaintext=known_plaintext,  # optional tutorial/review aid
    options=RdpDisplayOptions.standard(),
)
print_rdp_summary(summary)
write_rdp_summary_json(summary)
```

The JSON sidecar path is:

```text
artifacts/rdp_display_summary.json
```

This is the standard contract for human display and lightweight sharing. Tutorial,
LP-evidence, console, and debug views should use the same schema with different
`RdpDisplayOptions`; they should not invent separate summary formats.

If `RunSpec` is not supplied, the summary must warn that the problem/cipher/key
configuration is only reconstructed from result/report fields.

## Output surfaces

A GUI should read:

```text
output/
output/tutorials/
structured reports
artefact files
telemetry JSONL
tutorial summaries
artifacts/rdp_display_summary.json
```

Do not depend on exact human console wording.

## Minimal GUI run record

A useful GUI run record should contain:

```json
{
  "tutorial_id": "example_tutorial",
  "gate_profile": "release",
  "asset_profile": "lm2_baseline",
  "status": "pass",
  "acceptance_kind": "exact_or_threshold",
  "match_ratio": 1.0,
  "stop_reason": "success",
  "report_path": "output/tutorials/...",
  "display_summary_path": "output/tutorials/.../artifacts/rdp_display_summary.json",
  "telemetry_path": "output/tutorials/.../logs/app.jsonl",
  "warnings": []
}
```

The exact folder under `output/` may change between runs.

## Warnings a GUI should display

```text
known truth/key used
oracle stop score used
near-solve threshold used
optional asset missing
blocked tutorial entry
solver stopped by budget
diagnostic value is report-only
backend/device differs
standard display summary reconstructed without RunSpec
```

## Not a stable GUI contract

```text
exact console sentences
private helper modules
temporary output run-id names
internal test-only functions
release-contract evidence file layout
```

The release-contract folder exists for test-backed drift evidence. A GUI should
not treat it as the normal runtime interface.
