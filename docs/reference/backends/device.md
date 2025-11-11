# `backends/device.py`

> Purpose: resolve the execution device (CPU or CUDA) and provide a NumPy-like array API ("xp") that solvers and scorers can use without caring which backend is active.

## `get_device(requested=None)`
| Behaviour | Notes |
| --- | --- |
| Explicit `requested` of `"cpu"` or empty | Returns `("cpu", xp)` with the NumPy backend selected via `xp.select_backend("np")`. |
| CUDA requested (`"cuda"`, `"gpu"`, any truthy non-CPU string) | Tries CUDA backends in the order specified by `RDP_CUDA_BACKEND` (defaults to Torch, then CuPy). Falls back to CPU if none succeed. |
| Environment variables | `RDP_DEVICE` overrides the method argument. `RDP_CUDA_BACKEND` controls the preference order when both Torch and CuPy are available. |

Return value: tuple `(device_str, xp_module)` where `xp_module` exposes NumPy-compatible functions and `device_str` is `"cpu"` or `"cuda"`.

## Usage
```python
from rune_decrypter_prime.backends.device import get_device

device, xp = get_device("cuda")
arr = xp.asarray([1, 2, 3])  # torch.cuda or cupy array depending on availability
```

## Related Helpers
- `backends/xp.py::select_backend` - used internally to pick the concrete backend.
- `backends/xp.py::to_numpy` - re-exported here for convenience when results need to be converted to CPU arrays.

## Tests
- Exercised indirectly by CUDA parity tests (`tests/ciphers/test_columnar_device_parity.py`, `tests/scoring/test_backend_selection_and_parity.py`) since those suites rely on this resolver to switch between CPU/CUDA.

