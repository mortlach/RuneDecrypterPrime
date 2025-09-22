# rune\_decrypter\_prime — Friendly Tester README (v0.1.0)

**Goal:** help friendly testers run the preview, understand the moving parts, and try the included tutorials with minimal friction.

---

## 1) What this project is

`rune_decrypter_prime` is a modular cryptanalysis toolkit for a 29‑rune alphabet. It targets classical ciphers (monoalphabetic substitution, Vigenère, columnar transposition, etc.) using language‑model scoring plus search‑based optimisers (SA, GA, Hybrid).

You can declare cipher maths succinctly, choose a key model, and let an optimiser search for the best key against a statistical scorer.

---

## 2) Requirements and install

**Python:** 3.11+ on Windows, macOS, or Linux.
**Dependencies:**

* Required: `numpy`, `zstandard`
* Optional: `torch` (GPU acceleration if CUDA available)
* Build‑time (for C++ module): `pybind11`, `setuptools`, plus a C++20 compiler

Install the Python deps in your environment:

```bash
python -m pip install numpy zstandard
# Optional acceleration
python -m pip install torch       # if you want CUDA/torch backend
# For building the C++ scorer (see next section)
python -m pip install pybind11 setuptools
```

---

## 3) Fast language‑model scorer (C++)

The language‑model scorer uses a compiled extension `_fastlm`.

* **Windows (CPython 3.11, x64):** a prebuilt binary `_fastlm.cp311-win_amd64.pyd` ships in
  `rune_decrypter_prime/scoring/language_model/`. Nothing to build.
* **Other platforms / Python versions:** build the module once using the provided script:

```bash
# From the repository root:
python rune_decrypter_prime/scoring/language_model/setup_fastlm.py
```

The script:

* compiles `fastlm.cpp` (C++20; uses `pybind11`)
* drops `_fastlm.*.pyd/.so` next to `fastlm.cpp`
* verifies import automatically

**Compiler notes:**

* Windows: MSVC (Build Tools for Visual Studio) with C++ workload
* macOS: Xcode Command Line Tools (clang)
* Linux: `gcc` or `clang` and Python dev headers

If the build succeeds, `rune_decrypter_prime/scoring/language_model/_fastlm.*` will exist and `run.solve(...)` can use the fast scorer.

---

## 4) Representations at a glance

* **Runes:** 29‑symbol display alphabet; paste rune strings directly.
* **Indices:** `np.uint8` values in `[0..28]` for maths.
* **Runeglish:** accepts Latin letters and maps to runes for convenience.
* **WLI:** word/letter/interval mask used by the scorer; auto‑generated if omitted.

---

## 5) Architecture (one screen)

```
Ciphertext  +  CipherSpec  +  KeySpec  +  SolveSpec  →  optimiser loop → best key → Plaintext
                                         ▲
                                   Rune scorer
```

* **Ciphers:** local maths only. A shared **pipeline mixin** handles interruptors, transposition conventions, shapes, and validation.
* **Optimisers:** SA / GA / Hybrid explore key space and query the scorer.
* **Scorer:** unified façade (NumPy or Torch) backed by the C++ LM.
* **Device:** `"cpu"` (default) or `"cuda"`.
* **Telemetry:** every solve returns metadata (optimizer, scorer, device, timings, seeds).

---

## 6) Public API you’ll use

Import the UI layer:

```python
from rune_decrypter_prime.ui.api import CipherSpec, KeySpec, SolveSpec, run
from rune_decrypter_prime.ui.maps_api import define_map, define_cipher, preview as map_preview
from rune_decrypter_prime.ui.wrappers import by_name
```

### 6.1 `CipherSpec` — declare the cipher

```python
# Registry‑backed classic cipher
spec = CipherSpec.wrapper(name="substitution")

# Direct maths (Vigenère‑style): ct = (pt + k) mod 29
spec = CipherSpec.user_map2(function=lambda pt, k: (pt + k) % 29, N=29,
                            degeneracy="forbid", resolver="first", per_pos_limit=1)

# Two streams (advanced)
spec = CipherSpec.user_map3(function=lambda pt, k1, k2: (pt + k1 - k2) % 29)

# Lookup table variant
spec = CipherSpec.lookup(table=my_table, degeneracy="allow", per_pos_limit=2)
```

### 6.2 `KeySpec` — describe the key

```python
k_repeat = KeySpec.repeat(len=7)         # period‑7 repeating key
k_const  = KeySpec.const(value=3)        # additive constant
k_otp    = KeySpec.otp(stream=[...])     # explicit stream (known‑key preview)
k_perm   = KeySpec.permutation(len=15)   # permutation key (e.g., columns)
```

### 6.3 `SolveSpec` — choose an optimiser

```python
solve = SolveSpec.ga(population=128, generations=200, mut_prob=0.30)
# Aliases accepted: population/pop/pop_size; generations/steps/iters/iterations

solve = SolveSpec.sa(iters=50_000, sa_init_temp=1.0, sa_min_temp=0.02, sa_cooling=0.995)

solve = SolveSpec.hybrid(depth=2000, pop_size=96, gens=120, mut_prob=0.25, sa_iters=15_000)
```

### 6.4 `run` — the friendly entry points

```python
# Solve a ciphertext (returns a Solution with .plaintext and telemetry)
res = run.solve(text=ct, cipher=spec, key=k_repeat, solve=solve,
                device="cpu", scorer="rune",
                scorer_params=dict(direction="fwd", win=10, stride=1))
print(res.plaintext)

# Preview with a known key (one‑off encrypt/decrypt)
pt = run.preview(text=ct, cipher=spec, key=k_const, direction="decrypt", device="cpu")

# Convenience wrapper by name
spec, default_key = by_name.cipher_with_key("vigenere", key_len=7)
```

---

## 7) Tutorials (try these first)

Run the scripts directly from the repository root:

1. **Monoalphabetic — SA**
   `rune_decrypter_prime/tutorials/v1/dev/Tutorial_MonoSubstitution_SA.py`
2. **Monoalphabetic — GA**
   `rune_decrypter_prime/tutorials/v1/dev/Tutorial_MonoSubstitution_GA.py`
3. **Monoalphabetic — Hybrid**
   `rune_decrypter_prime/tutorials/v1/dev/Tutorial_MonoSubstitution_HYBRID.py`
4. **Vigenère (Generic Map API)**
   `rune_decrypter_prime/tutorials/v1/dev/Tutorial_Vigenere_GeneralMap.py`
5. **Columnar Transposition**
   `rune_decrypter_prime/tutorials/v1/dev/Tutorial_ColumnarTransposition.py`

Each prints progress and writes a JSON telemetry file under `tutorials/v1/out/logs/...`.

---

## 8) Scorer knobs (common ones)

```python
scorer_params=dict(
    direction="fwd",           # or "rev"; also accepts "reverse", "bwd", "back"
    win=10, stride=1,           # window size and stride
    se_mode="nose",            # or "wise"
    include_char=True,          # character channel
    use_word_breaks=True,
    char_weights={1: 0.6, 2: 0.4},
    objective="pct.logp.win10" # bounded [0,1]
)
```

---

## 9) Reproducibility

The aim is determinism, but GA uses shuffles; small run‑to‑run variation is expected unless all seeds are fixed. CPU runs with explicit seeds are the most repeatable. SA/Hybrid accept `seed`, `seed_keys`, or `initial_keys` via `SolveSpec`.

---

## 10) Troubleshooting

* **Missing `_fastlm`:** build it with `setup_fastlm.py` (Section 3). If you’re on Windows/CPython 3.11, the bundled `.pyd` should load automatically.
* **CUDA unavailable:** requesting `device="cuda"` falls back to CPU transparently.
* **Very short texts:** try `win=8..12` and include both 1‑ and 2‑gram channels.

---

## 11) Feedback

* Did install and the C++ build feel straightforward?
* Did the tutorials run end‑to‑end?
* Anything unclear or repeated in this README?

Thank you for testing!
