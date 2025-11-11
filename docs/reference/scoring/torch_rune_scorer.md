# `scoring/torch_rune_scorer.py`

> Purpose: CUDA/Torch implementation of the LMPrime scorer. Shares the same interface and telemetry contract as `scoring/rune_scorer.py` but runs windows/batches on the GPU when available.

## Notable Helpers
| Function | Description |
| --- | --- |
| `_xxh64_u32words_cpu` / `_xxh64_u32words_device` | Hashing utilities for deduplicating windows and seeding RNG streams on CPU/GPU. |
| `_to_torch_u8(...)` (see source) | Converts plaintext/WLI buffers to Torch tensors on the requested device. |

## `TorchRuneScorer`
- Mirrors the NumPy scorer but accepts `Device.CUDA` (resolved via `backends/device.py`).
- Chooses CUDA kernels for n-gram counting; falls back to CPU if Torch+CUDA is unavailable.
- Emits identical telemetry/last_stats payloads as the NumPy scorer so tests can compare both backends directly.

## Tests
- `tests/scoring/test_backend_selection_and_parity.py` - primary coverage; asserts CPU vs CUDA parity and ensures CUDA path is selected when available.
- `tests/scoring/test_pct_win10_stats_and_telemetry.py` - telemetry/threshold guarantees apply equally to Torch.

## Related Docs
- `docs/reference/scoring/rune_scorer.md` - CPU implementation details.
- `docs/guides/scoring_deep.md` - explains when to switch to CUDA and how deterministic seeds propagate through both implementations.

