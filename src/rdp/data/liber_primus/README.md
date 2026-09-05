# Liber Primus sources

These modules identify and read Liber Primus material, then build aligned ciphertext and word-location payloads. Source selection and a proposed solve recipe are distinct operations.

## Where to look

- [lp_source_catalogue.py](lp_source_catalogue.py) — Named source and solve-recipe entries.
- [lp_registry.py](lp_registry.py) — Typed page, locator and partition identities.
- [lp_adapter.py](lp_adapter.py) — Build solver payloads from selected material.
- [lp_transcript.py](lp_transcript.py) — Parse and index the transcription.
- [lp_main.py](lp_main.py) — Resolve identities against the main transcript.
- [lp_routes.py](lp_routes.py) — Line and spiral reading routes.
- [lp_ui_parse.py](lp_ui_parse.py) — Parse page tokens at a user-input boundary.
- [lp_data.py](lp_data.py) — Section and page data construction.

## Choices and extension

Start with `api.liber_primus.payload_from_label(...)` for a known label. Typed page and locator routes support more specific source selections. Changing a reading route changes the evidence supplied to a solve. A solved-source label does not imply that loading it has run a solver.

Continue with the [guide](../../../../docs/guides/liber_primus_typed_workflows.md) or the [package map](../../README.md).
