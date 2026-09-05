# Solver progress

Shared progress presentation for solver implementations.

## Where to look

- [mixin.py](mixin.py) — ProgressMixin for common reporting behaviour.
- [logger.py](logger.py) — SimpleLogger and the TQDM adapter.

## Choices and extension

Use these helpers when adding solver progress rather than embedding another progress loop. Report work performed in terms appropriate to the algorithm; iteration counts are not recovery percentages.

Continue with the [guide](../../../../docs/guides/telemetry.md) or the [package map](../../README.md).
