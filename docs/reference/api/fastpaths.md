# `api/fastpaths.py`

> Purpose: provide an early exit for "known key" scenarios (OTP/const keys) so tutorials/tests can decrypt without spinning up a solver. This keeps deterministic demos fast and ensures telemetry/logging still flow through the same code paths.

## `maybe_known_key_fastpath(...)`
| Parameter | Notes |
| --- | --- |
| `cipher`, `key` | Requires a `KeySpec` with plan `otp` or `const`. Other plans return `None` (pipeline continues normally). |
| `ciphertext`, `wli`, `device`, `encoding_dir` | Used to build a lightweight `CipherConfig`. WLI is normalised via `coerce_wli_for_config`. |
| `scoring`, `scorer_name`, `logging` | Passed through to `ProblemSpec` and solver configs so telemetry remains complete. |
| `telemetry_on` | Controls whether `finalize_solution` attaches telemetry/pipeline metadata. |

### Behaviour
1. Validates the key plan and constructs the concrete key stream (resizing OTP streams or filling const values).
2. Builds a `CipherConfig` and `ProblemInstance` identical to the main pipeline.
3. Configures an `EngineConfig` with a 1-width beam solver and `test_key` so the engine effectively just evaluates the known key once.
4. Calls `finalize_solution` to attach telemetry, plaintext views, and pipeline blocks before returning the `Solution`.

## Usage Example
Normally invoked internally by `api/pipeline.execute_run`. For unit tests you can call it directly:
```python
from rune_decrypter_prime.api.fastpaths import maybe_known_key_fastpath

solution = maybe_known_key_fastpath(
    cipher=cipher_spec,
    key=KeySpec.otp(stream=[1, 2, 3, 4]),
    ciphertext=ct_idx,
    wli=wli_spans,
    device=Device.CPU,
    scoring=scoring_cfg,
    scorer_name="rune",
    logging={"log_interval": 25},
    encoding_dir=Direction.LTR,
    telemetry_on=True,
)
if solution is None:
    # fallback to full pipeline
    solution = RunAPI.run(...)
```

## Tests
- Covered indirectly through tutorial regressions (OTP demos) and smoke tests that rely on deterministic known-key setups. Any failure in this helper bubbles up through `tests/smoke/test_runapi_determinism.py`.

## See Also
- `docs/reference/api/pipeline.md` - explains where the fast path is invoked before building the full problem instance.
- `docs/guides/quickstart.md` - Hands-on tutorials mention OTP/const paths that map to this helper.

