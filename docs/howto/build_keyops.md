# Build Your Own Cipher & KeyOps — Expert Guide

*Audience:* experienced users who want to add a new cipher and the matching KeyOps.

---

## 1) Outcome

You will:

* implement a bespoke cipher (pure `encode`/`decode`), **or** a General Map cell rule,
* define a clear **Key Model** (what a valid key looks like),
* implement **KeyOps** (deterministic moves within that space),
* register a wrapper so your cipher can be run from a tiny script,
* and smoke‑test it with a seeded run that writes artefacts under `output/`.

---

## 2) Contracts at a glance

### Cipher (bespoke)

* `encode(pt_indices, key, *, direction, tables, …) -> ct_indices`
* `decode(ct_indices, key, *, direction, tables, …) -> pt_indices`
* Pure functions; no hidden state; 29‑rune indices throughout.
* Round‑trip: `decode(encode(x, k), k) == x`.

### General Map (cell‑driven)

* `encode_cell(p: int, k: int, i: int) -> int | list[int]`
* `decode_cell(c: int, k: int, i: int) -> int | list[int]`
* Deterministic ordering for lists; **bounded** list sizes (keep small, e.g., ≤4).
* Position `i` optional; document indexing (0‑based; direction).

### Key Model

* Declarative structure (vector, permutation, tuple, named params with bounds).
* Must expose `normalise/validate/materialise` semantics (follow existing examples).

### KeyOps

* Deterministic given a seeded RNG.
* Provide: `random`, `mutate`, `neighbor`, `recombine`, `make_population`, `batch_neighbors` (align names/signatures with existing families in your repo).
* Preserve invariants (permutation stays a permutation; vectors remain in `[0,29)`).
* **Locality + ergodicity:** mostly small moves; occasional bigger jumps.

---

## 3) Step‑by‑step: bespoke cipher path

1. **Choose representation**

* If the rule is naturally symbol‑wise → consider a General Map first.
* If it has a clean global definition (e.g., columnar, matrix shuffle) → bespoke.

2. **Implement encode/decode (pure maths)**

```python
# Adjust imports to match your tree.
# Example: a tiny affine‑like toy cipher over mod 29
MOD = 29

def encode(pt_idx: list[int], key: dict, *, direction):
    a = key.get("a", 1) % MOD
    b = key.get("b", 0) % MOD
    return [ (a*x + b) % MOD for x in pt_idx ]

def decode(ct_idx: list[int], key: dict, *, direction):
    a = key.get("a", 1) % MOD
    b = key.get("b", 0) % MOD
    # modular inverse; ensure a is invertible mod 29
    ainv = pow(a, -1, MOD)
    return [ (ainv*(y - b)) % MOD for y in ct_idx ]
```

3. **Define the Key Model**

* **VectorKey (mod=29):** a list of integers for position‑dependent rules.
* **PermutationKey:** a bijection for columnar/ordering problems.
* **CompositeKey:** a tuple `(perm, vector)` when both are needed.
* Provide `normalise`/`validate` using the project’s existing helpers so your model integrates with KeyOps and tutorials.

4. **Implement KeyOps (deterministic)**

```python
# Pseudocode – mirror the signatures used by your existing KeyOps
class MyVectorKeyOps:
    def random(self, rng, length: int) -> list[int]:
        return rng.integers(0, 29, size=length).tolist()

    def neighbor(self, rng, key: list[int]) -> list[int]:
        k = key.copy()
        i = int(rng.integers(0, len(k)))
        k[i] = (k[i] + (1 if rng.integers(0,2) else -1)) % 29
        return k

    def mutate(self, rng, key: list[int]) -> list[int]:
        # slightly larger perturbation; still local
        k = self.neighbor(rng, key)
        if rng.random() < 0.1:
            j = int(rng.integers(0, len(k)))
            k[i], k[j] = k[j], k[i]
        return k

    def recombine(self, rng, a: list[int], b: list[int]) -> list[int]:
        cut = int(rng.integers(1, len(a)))
        return a[:cut] + b[cut:]

    # Provide make_population / batch_neighbors to enable vectorised scoring
```

* For **PermutationKey**, use adjacent swaps and cut‑and‑insert; always repair to a valid permutation.

5. **Register a wrapper**

* Create a small wrapper that binds: cipher maths + key model + KeyOps + sensible defaults, and add it to the registry so users can select your cipher by name.

6. **Smoke‑test from an IDE**

```python
# Minimal IDE script – adjust imports to your API surface
from rune_decrypter_prime.api import run  # copy from an existing tutorial

cfg = {
    "cipher": "my_affine",                 # your registry name
    "key_model": {"a": 5, "b": 7},        # or a vector/permutation spec
    "objective": "language_lm",
    "seed": 1234,
    "budget": {"iterations": 20_000},
    "telemetry": {"redact_identity": True},
}

pt = "ᚦᛖᚱᛖ ᚹᚪᛋ ᚪ ᛏᚪᛒᛚᛖ"
res = run(text=pt, **cfg)
print(res.best_key, res.best_plaintext)
```

---

## 4) Step‑by‑step: General Map (cell) path

1. **Define cell rules** (encode/decode)

```python
MOD = 29

def encode_cell(p: int, k: int, i: int) -> int:
    # example: position‑tinted add; deterministic
    return (p + k + (i % 7)) % MOD

def decode_cell(c: int, k: int, i: int) -> int:
    return (c - k - (i % 7)) % MOD
```

* If you need controlled ambiguity, return a **short** list (e.g., `[(base), (base+1)%29]`) and keep ordering deterministic.

2. **Pick a Key Model**

* Usually a **VectorKey(mod=29)** of length‐L. For position‑free rules, a single scalar is fine.

3. **KeyOps**

* Use small ±1 moves for vectors; occasional swaps for exploration; batch helpers for vectorised scoring.

4. **Register and smoke‑test**

* Bind the cell rules in your wrapper, set defaults, and run a tiny seeded example as above.

---

## 5) Designing for solvability (the A–B–C rules)

* **A — Ambiguity explosion:** cap per‑cell candidates; prefer singletons; if needed, use a beam at the pipeline level.
* **B — Broken invariants / bad KeyOps:** always preserve constraints; mix mostly‑local moves with rare larger jumps; repair deterministically.
* **C — Confused semantics:** identical scorer semantics across CPU/GPU; keep parameter names canonical; document indexing and direction once.

---

## 6) Blocks & composition

* Use **blocks** to express structure that isn’t naturally symbol‑wise (windowed transposes, stateful carries, long‑range mixing) and keep the cell stage simple.
* Blocks are reversible and round‑trip tested; compose them *before/after* your General Map.

---

## 7) Tests to add (fast and high‑signal)

* **Round‑trip** on random samples: `decode(encode(x,k),k) == x` when cells are 1→1.
* **KeyOps invariants**: 10k random operations preserve validity; neighbour is local.
* **Determinism**: same seed ⇒ same sequences of moves and the same best key on CPU.
* **Backend parity**: NumPy vs Torch scores match within FP tolerance for a fixed batch.
* **Toy solve**: a tiny plaintext/key is recovered within a small budget.

---

## 8) Performance notes

* Prefer **batch** proposals + batch scoring; it keeps the GPU busy and the CPU cache‑friendly.
* Keep heavy maths inside the scorer or the cell; avoid Python loops in the hot path.
* If you add controlled ambiguity, cap it aggressively (1–2 extra candidates per cell at most).

---

## 9) Privacy & telemetry

* Turn on `redact_identity=True` in public examples so META omits user/host while keeping seeds, configs, and device info.

---