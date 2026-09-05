# Logs, artifacts and random streams

These helpers handle durable run output and random-stream ownership. Structured progress-event definitions live in the neighbouring telemetry package.

## Where to look

- [run_logger.py](run_logger.py) — RunLogger and file logging.
- [logging_adapter.py](logging_adapter.py) — Module-level logging adapter.
- [artifact_policy.py](artifact_policy.py) — Artifact paths and portable serialisation.
- [rng.py](rng.py) — RNGController and derived random streams.

## Choices and extension

Configure output through `api.LoggingConfig` and the run request. Keep paths portable when sharing results. A seed identifies the random recipe; retain the input, settings and backend context with it to make the run interpretable.

Continue with the [guide](../../../docs/guides/outputs.md) or the [package map](../README.md).
