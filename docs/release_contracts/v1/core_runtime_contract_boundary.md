# Core runtime contract boundary

Status: D3-0c contract freeze baseline.

## Rule

The public API may accept friendly user-facing shapes such as dictionaries, strings, and aliases. The core runtime must not.

Before a run reaches `ProblemSpec`, `ProblemInstance`, `DecryptionProblem`, or the core engine builders, user-facing shapes must already have been normalised into canonical config objects.

## Canonical runtime objects

The core runtime boundary is:

- `ProblemSpec.cipher_cfg`: `CipherConfig`
- `ProblemSpec.scorer_params`: `ScoringConfig`
- `DecryptionProblem.c_cfg`: `CipherConfig`
- `DecryptionProblem.s_cfg`: `ScoringConfig`
- `build_cipher(cfg_cipher)`: `CipherConfig`
- `build_scorer(c_cfg, s_cfg)`: `CipherConfig` plus `ScoringConfig`

Dictionaries, `SimpleNamespace`, loose objects, and config-like bags are rejected at this boundary.

`CipherConfig.spec` is an explicitly named slot for typed cipher-plugin specification objects only. It must not be used as a generic container for upstream config dictionaries or arbitrary runtime settings. Any plugin that uses it must define and document the concrete spec object it expects.

## Normalisation boundary

User-facing scorer parameter dictionaries remain accepted by `RunAPI.run(...)`. They are normalised in `api/run.py` before `execute_run(...)` builds the canonical `ScoringConfig` passed into core.

`RunConfig.from_dict(...)` remains a config-construction helper. It is a boundary helper, not runtime solver state. Runtime materialisation from `RunConfig` still uses typed `CipherConfig`, `ScoringConfig`, and `SolverConfig` fields after construction.

Config dataclasses may still normalise nested config-construction inputs, for example:

- `RunConfig.from_dict(...)`
- `ScoringConfig(objective={...})`
- `CipherConfig(interruptors_cfg={...})`
- `HardCribConfig` normalisation

These are construction-boundary behaviours, not runtime dict acceptance.

## Layout guardrails

The public config import surface is the package `rune_decrypter_prime.core.config`, backed by:

`src/rune_decrypter_prime/core/config/__init__.py`

There must not also be a sibling module file:

`src/rune_decrypter_prime/core/config.py`

D3-0b/D3-0c delete that file because Python resolves `rune_decrypter_prime.core.config` to the package directory, not to the sibling module file. Keeping both creates an ambiguous layout and makes the file-level shim unreachable.

The guardrail tests enforce:

- no module/package name collisions under `src/rune_decrypter_prime/core`;
- no aggregate `from rune_decrypter_prime.core.config import ...` imports inside core runtime files;
- no hidden config getter helpers such as `_cfg_get`, `_config_get`, `_get_cfg`, or `_get_config` in core runtime or the NumPy scorer;
- no dict-like config acceptance in runtime paths;
- direct attribute access after `CipherConfig` / `ScoringConfig` type checks;
- documented construction-boundary and payload exceptions only.

## Import rule inside core runtime

Core runtime files must import exact config submodules, for example:

```python
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.config.solver import SolverConfig
from rune_decrypter_prime.core.config.run import RunConfig
```

Core runtime files must not import from the aggregate package surface:

```python
from rune_decrypter_prime.core.config import CipherConfig
```

The aggregate package re-export remains public-facing and may be used by API modules, tutorials, and external callers.

## Removed runtime probes

D3-0 removes hidden config probing from the core runtime path:

- `core/engine/builders.py` no longer has `_cfg_get` and no longer accepts mapping-like cipher/scorer configs.
- `scoring/rune_scorer.py` no longer has `_cfg_get`; the NumPy scorer now requires `CipherConfig` and `ScoringConfig`.
- `core/problem/runtime.py` no longer converts a dict `c_cfg` into `CipherConfig` inside `DecryptionProblem`.
- `core/problem/runtime.py` no longer checks dict scorer config while resolving hard-crib settings.
- `core/engine/engine.py` no longer treats `ProblemSpec.scorer_params` as either a dict or object.
- `core/solver_engine.py` no longer accepts dict-like optimiser config in the legacy helper.

D3-0b tightens this further:

- `core/config.py` is removed; `core/config/__init__.py` is the only public re-export surface.
- Core runtime files import exact config submodules rather than the aggregate package.
- `RuneScorer` uses direct `scorer_cfg.field` access after checking `scorer_cfg` is `ScoringConfig`.
- `DecryptionProblem` uses direct `self.c_cfg.field` and `self.s_cfg.field` access for canonical config fields.
- `CipherConfig.spec` is an explicit optional field so degeneracy handling does not probe for hidden attributes.

## Retained compatibility surfaces

`src/rune_decrypter_prime/core/config/__init__.py` remains the V1 public re-export surface for existing imports such as:

```python
from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
```

Telemetry dictionaries, scorer report/stat dictionaries, and key-operation hint dictionaries remain allowed as payload data. They are not runtime config objects. Any such exception must be named in `tests/contracts/test_core_layout_guardrails.py`.

## Acceptance tests

The focused D3-0/D3-0b boundary tests live in:

- `tests/core/test_core_runtime_contract_boundary.py`
- `tests/contracts/test_core_layout_guardrails.py`

They lock the following behaviours:

- `ProblemSpec` accepts canonical `CipherConfig` and `ScoringConfig`.
- `ProblemSpec` rejects dict `cipher_cfg`.
- `ProblemSpec` rejects dict `scorer_params`.
- `DecryptionProblem` rejects dict `c_cfg`.
- `DecryptionProblem` rejects dict `s_cfg`.
- `build_scorer` accepts canonical `CipherConfig` and `ScoringConfig` without monkeypatching core runtime.
- `build_scorer` rejects dict `c_cfg`.
- `build_scorer` rejects dict `s_cfg`.
- `RuneScorer` rejects dict `scorer_cfg` before any backend or asset load.
- `RunAPI.run(...)` still accepts user-facing `scorer_params` dicts and normalises them before core.
- `rune_decrypter_prime.core.config` resolves to `core/config/__init__.py`.
- no `core/config.py` sibling module exists.
- no hidden config getter helpers remain in core runtime or the NumPy scorer.
- no aggregate config imports remain inside core runtime.
