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

## Output surfaces

A GUI should read:

```text
output/
output/tutorials/
structured reports
artefact files
telemetry JSONL
tutorial summaries
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
