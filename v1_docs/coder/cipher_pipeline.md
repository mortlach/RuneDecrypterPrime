# Cipher Pipeline

Status: staged V1 draft

Owner paths:
- `src/rdp/ciphers/`
- `src/rdp/api/specs.py`
- `src/rdp/core/problem/runtime.py`

Related tests:
- `tests/ciphers/`
- `tests/api/`
- `tests/core/`
- `tests/pipeline/`

Stability:
- Semi-stable contributor surface

## Purpose

The cipher layer transforms text for a supplied key. It does not search for
keys, rank plaintext, decide stop reasons, or write reports.

## What This Layer Owns

- concrete encrypt/decrypt implementations
- cipher registration
- cipher-specific config interpretation
- text/key transposition plumbing through `CipherPipelineMixin`
- interruptor removal/reinsertion where supported
- batch decrypt/encrypt kernel shape contracts
- candidate expansion hooks such as `candidates_for(...)` where a cipher
  supports degenerate mappings

## What This Layer Must Not Own

- key generation or mutation
- solver search strategy
- scoring/ranking policy
- truth/oracle decisions
- report-only diagnostic ranking effects
- output artifact writing

## Main Objects

| Object | Owner path | Role |
| --- | --- | --- |
| runtime registry | `src/rdp/ciphers/cipher_runtime_registry.py` | Maps each canonical identity to its exact constructor. |
| `KeyedCipherBase` | `src/rdp/ciphers/base_keyed_cipher.py` | Minimal base for keyed ciphers. |
| `CipherPipelineMixin` | `src/rdp/ciphers/ciphers_pipeline.py` | Shared encrypt/decrypt orchestration. |
| concrete cipher classes | `src/rdp/ciphers/` | Implement cipher-specific core kernels. |
| typed cipher specs | `src/rdp/api/specs.py` | Translate public typed choices to core cipher config. |

## How It Fits Into A Run

```text
CipherSpec / wrapper
  -> CipherConfig
  -> concrete cipher instance
  -> DecryptionProblem
  -> solver asks problem.evaluate_keys(...)
  -> cipher decrypts candidate keys
  -> scorer ranks plaintext
```

`DecryptionProblem` builds keyops from cipher/key config and calls cipher
decrypt during evaluation.

## Contracts And Invariants

- Concrete ciphers declare a keyops family and fixed key length when required.
- Batch core hooks should accept candidate key batches and return batch
  plaintext/ciphertext arrays.
- Keys should already be normalised by keyops before hot-path decrypt.
- Interruptor and transposition handling should stay consistent across ciphers.
- A cipher should fail clearly when config is invalid.

## Determinism Notes

- Ciphers should be pure for a given ciphertext/key/config.
- Ciphers should not repair random or invalid keys silently.
- Any candidate expansion cap must be explicit and reportable by the calling
  runtime.

## Report And Telemetry Outputs

The cipher layer may contribute config names, key lengths, transposition choices,
interruptor settings, and degeneracy settings to runtime metadata. It should not
write reports itself.

## Extension Checklist

1. Add the concrete cipher under `src/rdp/ciphers/`.
2. Register it through the cipher registry when it should be buildable by name.
3. Add or update API wrapper routing if it should be friendly/public.
4. Define keyops family and key length rules.
5. Add focused tests under `tests/ciphers/`.
6. Add run/API tests if it is exposed through `api.run`.
7. Update docs and public API allowlist only if the new surface is public.

## What Not To Rely On

- Private helper methods in concrete cipher classes.
- Prototype cipher-development workspaces; supported runtime code has one owner
  under `src/rdp/ciphers/`.
- Exact internal array layout beyond documented batch contracts.
