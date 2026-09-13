# Array and device support

This package contains low-level array and device adapters used by runtime code.

`xp.py` owns the NumPy, CuPy and Torch conversion/availability helpers.

`device.py` contains device-selection support.

The existence of an adapter does not make every backend/device combination part
of the supported public scoring surface.

Public runs select the compute device through `RunSpec` and the scoring backend
through `ScoringConfig`.

See [CPU, CUDA and scoring](../../../docs/setup/scorer_backend_selection.md) and
[Scoring and language models](../../../docs/architecture/scoring_and_language_models.md).
