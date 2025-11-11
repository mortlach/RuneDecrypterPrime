# `rune_decrypter_prime/ciphers` — Overview & Authoring Guide

This folder contains **cipher implementations** used by the solver. Ciphers are deliberately thin: they implement only the cryptographic mapping and leave **key generation, normalization, mutation, and crossover** to the **KeyOps** layer. Optimizers never depend on cipher-specific code; they work through a **generic Problem → KeyOps → evaluate** pipeline.

---

## Key ideas

* **Keys are typed.** A cipher declares the *family* of its key:

  * **Permutation** (`"perm"`): keys are permutations over positions or symbols (e.g., Substitution, Columnar).
  * **Vector** (`"vector"`): keys are length-K vectors of small integers (e.g., Vigenère shifts).
  * Future types (affine, matrix, mixed) can be added via new KeyOps without touching optimizers.

* **Problem constructs KeyOps.**
  Ciphers **do not** construct KeyOps. Each cipher declares:

  * `keyops_family` (string) — e.g., `"perm"` or `"vector"`.
  * `key_length` (int or property) — fixed key size `K` for this instance.
    The `DecryptionProblem` uses these to build `problem.keyops` once.

* **Decrypt hot path is pure and fast.**
  Decrypt functions assume the key is already the right shape and valid. KeyOps is responsible for normalization/repair; optimizers call KeyOps verbs before scoring.

* **Batch first.**
  All core decrypt/encrypt routines accept keys of shape **`[B, K]`** and must return **`[B, L]`** plaintext/ciphertext arrays. Single keys `[K]` are allowed as a shorthand and should be upcast to `[1, K]` internally.

* **Index space & dtype.**
  Use **`np.uint8`** for tokens/indices and return `uint8`. Temporary arithmetic can upcast (e.g., to `int16`) and cast back.

---

## Minimal cipher contract

Every cipher must:

1. **Declare key family and length**

   ```python
   keyops_family = "perm"     # or "vector", etc.
   key_length = 6             # fixed K for this instance (may be set in __init__)
   ```

2. **Implement a batch core**

   * `_core_decrypt_batch(ct_tr: [L] u8, keys_tr: [B,K] u8) -> [B,L] u8`
   * Optionally `_core_encrypt_batch(pt_tr: [L] u8, keys_tr: [B,K] u8) -> [B,L] u8` (used by tutorials/tests; not required by optimizers)

3. **Inherit the pipeline mixin**

   ```python
   from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin
   class MyCipher(CipherPipelineMixin, KeyedCipherBase): ...
   ```

   The mixin handles text/key transpositions, interruptors, and keeps the public `.decrypt()`/.`encrypt()` stable across ciphers.

4. **Avoid KeyOps inside the cipher.**
   Do not normalize or mutate keys in decrypt. Keep decrypt deterministic and vectorized.

---

## Base helpers

Use the small base to keep ciphers uniform:

```python
from rune_decrypter_prime.ciphers.base_keyed_cipher import KeyedCipherBase
```

* Provides `_as_u8()` helpers.
* Documents the expected contract.
* Keeps dtype/shape handling consistent.

> The typical inheritance is: `class MyCipher(CipherPipelineMixin, KeyedCipherBase)`

---

## Shapes and conventions

* **Ciphertext/Plaintext:** `[L]` `uint8` indices in the working alphabet (e.g., 29 runes).
* **Key:** `[K]` `uint8` or `[B, K]` `uint8`.
* **Return:** `[B, L]` `uint8` for batch cores. The mixin adapts public decrypt to return `[L]` for single key.

**Permutation keys.** Represent permutations as arrays where **index = physical position** and **value = mapped position/symbol**. If a cipher historically used a different order (rank vs position), convert once in the cipher (or in `PermutationKeyOps.normalize`) and keep the canonical representation internally.

**Vector keys.** Represent shifts/values modulo `A` (alphabet size). At text position `i`, the active key slot is `i % K`.

---

## Examples

### 1) Substitution (permutation, `K=A`)

* `keyops_family = "perm"`
* `key_length = A` (alphabet size)
* Decrypt: **inverse map** `pt = key[ct]`
  (If tutorials pass forward map `pt->ct`, invert once locally for that code path.)

### 2) Columnar Transposition (permutation, `K=columns`)

* `keyops_family = "perm"`
* `key_length = n_cols`
* Decrypt pipeline:

  1. Compute column lengths for `ceil(L/K)` rows.
  2. Slice columns from ciphertext in the **key-given read order**.
  3. Reconstruct plaintext by **row-wise** interleave.

### 3) Vigenère (vector, `K=period`)

* `keyops_family = "vector"`
* `key_length = period`
* Decrypt: `pt = (ct - key[pos % K]) mod A`
  Vectorize by preparing `cols = arange(L) % K` then `keys[:, cols]`.

### 4) Generic Map (vector, function or lookup)

* `keyops_family = "vector"`
* `key_length = period`
* Build encoder/decoder tables once.
  Decrypt uses a decoder table with a deterministic policy in case of degeneracy (e.g., first inverse).

---

## How KeyOps and ciphers interact

* The **Problem** constructs `problem.keyops` using `cipher.keyops_family` and `cipher.key_length`.
* **Optimizers** ask KeyOps for:

  * `random(rng)` initial keys,
  * `mutate(key, rng)` and `crossover(p1, p2, rng)`,
  * optional batch helpers (e.g., `make_population`, `expand_position`, `batch_neighbors`).
* Keys created/modified by KeyOps are passed to `Problem.evaluate_keys(...)`, which calls `cipher.decrypt(...)`. Decrypt assumes keys are valid shape/type and performs no repairs.

This separation allows new key families to be introduced by adding KeyOps subclasses only; optimizers remain unchanged.

---

## Adding a new cipher (checklist)

1. **Decide the key family and K.**

   * Permutation or vector?
   * How is `K` determined (config, alphabet, period)?

2. **Create the class.**

   ```python
   from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin
   from rune_decrypter_prime.ciphers.base_keyed_cipher import KeyedCipherBase
   from rune_decrypter_prime.ciphers.registry import register_cipher

   @register_cipher("my_cipher")
   class MyCipher(CipherPipelineMixin, KeyedCipherBase):
       keyops_family = "perm"  # or "vector"
       def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
           super().__init__(text_transposition=text_transposition, key_transposition=key_transposition)
           self.key_length = int(getattr(cfg, "key_length"))  # set K
           self.cfg = cfg

       def _core_decrypt_batch(self, ct_tr: np.ndarray, keys_tr: np.ndarray) -> np.ndarray:
           # implement vectorized batch decrypt here, return [B,L] uint8
           ...
   ```

   * Register with one or more names via `@register_cipher`.

3. **Implement `_core_decrypt_batch` (and `_core_encrypt_batch` if you need it).**

   * Accept `keys_tr` as `[B, K]` or `[K]` (upcast to `[B, K]`).
   * Use `np.uint8` throughout and return `np.uint8`.

4. **Do not construct KeyOps.**
   The Problem will attach it once based on your declarations.

5. **Avoid per-candidate normalization.**
   If a legacy path needs repair, do it in one place (`KeyOps.normalize`) or at the edge (tutorial helpers), not in decrypt.

6. **Test with single and batch keys.**

   * Single key `[K]` → output `[L]`
   * Batch keys `[B, K]` → output `[B, L]`

---

## Common pitfalls

* **Normalizing in decrypt.**
  This adds hidden cost and can mask bugs. Keep decrypt pure; normalize in KeyOps or upstream tests/tutorials.

* **Mismatched permutation convention.**
  Decide whether values are *positions* or *ranks*; convert once and document it. The canonical internal convention is:

  * index = physical position
  * value = mapped position/symbol

* **Forgetting to set `key_length`.**
  The Problem needs `K` to build KeyOps. Provide it via config or compute it deterministically.

* **Mixed dtypes.**
  Always coerce inputs to `np.uint8` and return `np.uint8`. Upcast only for intermediate math.

---

## FAQ

**Q: How do I support GPU?**
If you need Torch, pick the backend in `__init__` and provide Torch kernels parallel to NumPy ones, returning NumPy arrays at the boundary. See `Vigenère` and `GenericMapCipher` examples.

**Q: How do I handle multiple public names (aliases)?**
Use multiple `@register_cipher("alias")` decorators.

**Q: Do ciphers need to know about WLI (word-like intervals)?**
No. WLI is consumed by scorers. Ciphers operate only on index sequences.

---

## Files to look at

* `base_keyed_cipher.py` — small base that keeps ciphers uniform.
* `substitution_cipher.py` — permutation key, straightforward decrypt `pt = key[ct]`.
* `columnar_transposition_cipher.py` — permutation key, row/column reconstruction.
* `vigenere_cipher.py` — vector key, mod-A arithmetic, optional Torch path.
* `generic_map_cipher.py` — function/lookup vector cipher with encoder/decoder tables.

---

By following this pattern—declare the key family and length, implement a clean batch decrypt core, and keep KeyOps concerns out of the cipher—you get ciphers that are **fast, testable, and future-proof**. Adding new key types later won’t require solver changes; only a new KeyOps subclass and a cipher that declares it.
