# Compute device and scorer backend

RDP separates two choices that are easy to conflate:

- `RunSpec.compute_device` says where the run is requested to execute;
- `ScoringConfig.backend` selects the scoring implementation.

CPU is the public compute-device default. Installing or verifying CUDA only
makes CUDA available; it does not change that default.

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

For GPU execution, request `api.ComputeDevice.CUDA`. `ScorerBackend.AUTO`
resolves the scoring backend against the requested device and available
capabilities.

An explicitly requested unavailable backend or CUDA device blocks clearly. RDP
does not quietly fall back to a different device or scoring route.

NumPy is the reference CPU scoring route. Optional Torch/native routes must
preserve the same scoring objective and reporting contract. The effective
backend, compute device, dtypes and seed information are retained in the run's
reporting and reproducibility metadata.

Serialized configuration can use `ScoringConfig.from_dict`; ordinary Python
code should use the typed enum values directly.

For installation and hardware verification, see
[CUDA provisioning](../development/cuda_installation.md).
