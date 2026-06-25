# Stability surface

Status: expert integrator guide

This page tells expert users and GUI/front-end developers what they can rely on.

## Stable user-facing concepts

These are intended to be stable enough for users and GUIs:

```text
tutorial manifest
tutorial runner
gate profile
asset profile
tutorial status
source label concept
output/ generated-output root
reports, artefacts, and telemetry as evidence surfaces
exact solve versus partial recovery
known truth/key visibility
```

## Stable enough paths

```text
tutorials/v1/tutorial_manifest_v1.json
tutorials/v1/run_tutorials.py
docs/README.md
docs/expert/gui_interface_contract.md
output/
```

## Test-backed evidence surface

This path is intentionally retained for contract tests:

```text
docs/release_contracts/v1/
```

It is useful and important, but it is not the GUI runtime interface and not the
beginner docs path.

## Not stable as public interface

Do not build user tools around:

```text
exact console wording
private helper modules
temporary output folder names
internal test-only helpers
release-contract evidence file layout
```

## Review rule

A change that affects a stable user-facing concept should update:

```text
docs/guides/
docs/expert/
tutorials/v1/tutorial_manifest_v1.json
tests/contracts/
```

A GUI should fail clearly or show a warning when a field it expects is missing.
