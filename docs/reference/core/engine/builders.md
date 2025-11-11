# `core/engine/builders.py`

> Purpose: factory helpers that construct the solver-facing cipher/scorer objects from `CipherConfig`. These live close to the engine to avoid importing heavy modules in user-facing code.

## Functions
- `build_cipher(cfg_cipher)` - Instantiate the concrete cipher object based on the `CipherConfig` produced by the wrappers/registry module. Ensures the solver receives encrypt/decrypt methods plus metadata required for telemetry.

The file also houses other builders (`build_scorer`, etc.) in the source; they follow the same pattern: accept a config dataclass, return fully initialised objects ready for the solver engine.

## Usage
Called by `core/engine/engine.solve` (via `ProblemInstance`)-not intended for direct Hands-on use.

## Tests
- Covered indirectly by every solver/cipher regression (`tests/ciphers/test_columnar_device_parity.py`, `tests/solvers/test_permutation_optimizers.py`) since failing builders would panic before solvers run.

## Related Docs
- `docs/reference/api/wrappers/registry.md` - upstream creator of the `CipherConfig` consumed here.
- `docs/reference/core/engine/engine.md` - shows where builders are invoked inside the solve loop.

