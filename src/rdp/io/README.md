# Logs, artifacts and random streams

This package owns durable run-output helpers and random-stream support.

## Main owners

- `run_logger.py` owns run-file logging
- `logging_adapter.py` provides module logging integration
- `artifact_policy.py` owns artifact paths and portable serialisation rules
- `rng.py` owns derived random streams used by internal workflows

Public saved output is configured through `api.LoggingConfig`.

Telemetry is a separate execution-observation layer.

See [Outputs](../../../docs/guides/outputs.md),
[Telemetry](../../../docs/guides/telemetry.md) and
[Repeating a run](../../../docs/guides/reproducibility.md).
