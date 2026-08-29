# Scorer backend selection

Public callers select scoring backend and compute device with typed values:

```python
from rdp import api

scoring = api.ScoringConfig(
    objective=api.advanced.ScoringObjective.average_log_probability(),
    backend=api.advanced.ScorerBackend.NUMPY,
)
request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=8, rounds=2, seed=7),
    scoring=scoring,
    compute_device=api.ComputeDevice.CPU,
)
```

`ScorerBackend.AUTO` resolves according to the requested compute device and
available capabilities. An explicitly requested unavailable backend or CUDA
device blocks clearly; it does not silently fall back.

NumPy is the reference CPU route. Optional Torch/native routes must preserve the
same objective and reporting contract. Backend, device, dtype and capability
status are recorded in `RunResult.scorer_report` and reproducibility metadata.

Serialized configuration may use `ScoringConfig.from_dict`; ordinary code uses
typed enums directly.
