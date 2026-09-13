# Execution telemetry

Telemetry records what the runtime did: run and solver events, progress, pipeline context and scoring details. It supports inspection without becoming part of candidate ranking.

## Where to look

- [events.py](events.py) — Run and solver start, progress and end events.
- [bag.py](bag.py) — Mutable telemetry collection.
- [pipeline.py](pipeline.py) — Pipeline metadata and final run metadata.
- [schema.py](schema.py) — Canonical backend and device labels.
- [scoring.py](scoring.py) — Scoring telemetry helpers.

## Choices and extension

`RunSpec.telemetry_enabled` controls telemetry collection. Durable logging is a separate request choice. When adding an event, define its payload and preserve its meaning when reporting is disabled; progress reporting must not change which key is selected.

Continue with the [guide](../../../docs/guides/telemetry.md) or the [package map](../README.md).
