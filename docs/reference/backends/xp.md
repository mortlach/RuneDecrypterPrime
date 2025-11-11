# `backends/xp.py`

> Purpose: lightweight abstraction layer that hides the differences between NumPy, Torch, and CuPy. Provides capability detection, device naming, and conversion helpers so higher-level code can write array maths once.

## Key Helpers
| Function | Description |
| --- | --- |
| `_try_import(name)` | Best-effort import used when probing for backends. |
| `get_versions()` | Returns a dict of available library versions (NumPy, Torch, CuPy) for telemetry. |
| `have_cupy()` / `have_torch_cuda()` / `have_any_cuda()` | Capability checks used by device selection and diagnostics. |
| `device_name(requested)` | Produces a human-readable label ("cpu", "cuda:torch", "cuda:cupy"). |
| `sync()` | Calls the appropriate synchronisation primitive (`torch.cuda.synchronize()`, `cupy.cuda.Stream.null.synchronize()`) when a GPU backend is active; no-op on CPU. |
| `select_backend(requested)` | Core factory that returns `(device_name, xp)` where `xp` exposes a NumPy-like API implemented via NumPy/Torch/CuPy depending on availability. |
| `to_numpy(x)` | Converts arrays/tensors from the selected backend back to NumPy for logging/telemetry. |

## Usage
```python
from rune_decrypter_prime.backends.xp import select_backend, to_numpy

device, xp = select_backend("torch")  # or "np" / "cupy"
arr = xp.asarray([1, 2, 3])
numpy_arr = to_numpy(arr)
```

## Tests
- Capability checks are indirectly exercised by CUDA parity suites (e.g., `tests/ciphers/test_columnar_device_parity.py`, `tests/scoring/test_backend_selection_and_parity.py`) since failures in backend selection would surface there.

## Related Docs
- `docs/reference/backends/device.md` - high-level resolver that invokes `select_backend`.
- `docs/reference/scoring/rune_scorer.md` - describes how scorers consume the returned `xp`.

