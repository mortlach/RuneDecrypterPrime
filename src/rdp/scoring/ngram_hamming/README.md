# Phrase diagnostics

This folder implements n-gram Hamming phrase diagnostics. In V1 these are report-only evidence, not an additional production ranking lane.

## Where to look

- [reference.py](reference.py) — Phrase profiles, entries and reference scanning.
- [bridge.py](bridge.py) — Profile selection and clustered phrase evidence.
- [report_only_telemetry.py](report_only_telemetry.py) — Attach diagnostic evidence to reports.
- [fast_backend.py](fast_backend.py) — Native scanner adapter.
- [setup_ngram_hamming_fast.py](setup_ngram_hamming_fast.py) — Build the optional native scanner.

## Choices and extension

Profiles and diagnostic output can be explored when inspecting candidates. Enabling a report must not alter solver ranking or stopping. Promoting a diagnostic into scoring is a separate design decision.

Continue with the [guide](../../../../docs/release_contracts/v1/report_only_diagnostics_contract.md) or the [package map](../../README.md).
