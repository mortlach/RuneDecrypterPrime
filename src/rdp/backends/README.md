# Array and device support

This folder contains array-backend adapters and device helpers used by runtime code. It keeps low-level array creation and conversion in a small implementation layer.

## Where to look

- [xp.py](xp.py) — NumPy, CuPy and Torch adapters plus availability and version probes.
- [device.py](device.py) — Device selection helper.

## Choices and extension

Public compute-device and scoring-backend choices are governed by the supported API and capability checks. The presence of an adapter here does not make every backend/device combination a supported scoring configuration. Check the backend guide before changing a run.

Continue with the [guide](../../../docs/setup/scorer_backend_selection.md) or the [package map](../README.md).
