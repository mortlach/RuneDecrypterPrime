# Key Pipeline

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/keyops/`
- `src/rdp/core/types.py`
- `src/rdp/core/problem/runtime.py`

Related tests:
- `tests/keyops/`
- `tests/core/`
- `tests/ciphers/`
- `tests/solvers/`

Stability:
- Public V1 surface for `KeySpec`
- Semi-stable contributor surface for keyops families

## Purpose

The key pipeline turns a front-door `KeySpec` into runtime key operations that
solvers can use without knowing cipher details.

## What This Layer Owns

- user-facing key plans through `KeySpec`
- keyops families and registry
- key normalisation and validation
- random key generation
- mutation, neighbour, recombination, and population helpers
- batch neighbour generation
- key capability reporting through `KeyCaps`

## What This Layer Must Not Own

- cipher math
- scorer ranking
- solver stop policy
- report writing
- hidden truth/oracle behaviour

## Main Objects

| Object | Owner path | Role |
| --- | --- | --- |
| `KeySpec` | `src/rune_decrypter_prime/api/specs.py` | Public declarative key plan. |
| `KeyOpsFamily` | `src/rdp/core/types.py` | Canonical runtime family enum. |
| `KeyCaps` | `src/rune_decrypter_prime/keyops/base_keyops.py` | Capability description for a keyops class. |
| `KeyOpBase` | `src/rune_decrypter_prime/keyops/base_keyops.py` | Base class and verb registry. |
| keyops registry | `src/rune_decrypter_prime/keyops/registry.py` | Constructs keyops by family. |
| concrete keyops | `src/rune_decrypter_prime/keyops/` | Implement family-specific key verbs. |

## How It Fits Into A Run

```text
KeySpec
  -> CipherConfig key fields
  -> cipher declares keyops family and length
  -> DecryptionProblem creates keyops
  -> solver calls keyops verbs
  -> problem evaluates generated keys
```

## Contracts And Invariants

- `KeySpec` is the public key-plan object.
- Runtime keyops classes own validation, normalisation, and mutation.
- Solvers should call keyops verbs rather than special-case key shapes.
- `caps.length` must match the resolved key length.
- `caps.ops` should describe optional verbs a solver may use.

## Determinism Notes

- Keyops randomness must come from the supplied RNG.
- Same seed and same config should produce repeatable candidate generation.
- Invalid seed keys should block clearly rather than fall back silently.

## Report And Telemetry Outputs

Key-related report surfaces may include key plan, key length, recovered key
preview, seed-key diagnostics, and keyops capability hints. Do not expose hidden
truth keys as production ranking inputs.

## Extension Checklist

1. Add or reuse a `KeySpec` plan.
2. Add a `KeyOpsFamily` value only when a new family is truly needed.
3. Implement a keyops class with required verbs: `random`, `normalize`, and
   `mutate`.
4. Register the keyops family.
5. Add tests under `tests/keyops/`.
6. Add solver/cipher tests if existing solvers will consume the new family.
7. Update docs after the source/test path is verified.

## What Not To Rely On

- Internal keyops repair helpers.
- Development keyops under `src/rune_decrypter_prime/keyops/dev/` unless
  promoted explicitly.
- Direct mutation of private `KeySpec` fields such as `_align_offset`.
