
## 1) What this project is

`rune_decrypter_prime` is a **modular, extensible cryptanalysis toolkit** for a 29‑rune alphabet. Its design is deliberately plug‑and‑play:

* **Ciphers** can be added from the simplest Caesar shift to more complex systems like Enigma by defining their maths once.
* **Keys** are described declaratively, so new key models drop in cleanly.
* **Optimisers** (SA, GA, Hybrid) are interchangeable, and new search strategies can be introduced without changing cipher code.
* **Scorers** are modular: current language‑model scoring works with NumPy, Torch, or the fast C++ backend, and future scoring methods can be slotted in.

This architecture makes the system *infinitely extensible* — you can grow from basic teaching ciphers to complex research‑grade experiments.

You declare cipher maths succinctly, choose a key model, and let an optimiser search for the best key against a statistical scorer.

(atm docs provided by a llm near you, so, you know ... )  

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

---

## What we care about (philosophy)

* **Determinism.** Same seed + same config → same result, byte‑for‑byte. We compare ideas fairly and don’t keep rediscovering the same solution.
* **Separation of concerns.** Cipher maths, keys, search, and scoring are cleanly split. Swap one without surprising the others.
* **Explicit over clever.** Strong enums and typed configs. No hidden globals, no silent I/O.
* **Observability.** Every run leaves a tidy trail under `output/…`: metadata, logs, and artefacts (files land where you can find them later).
* **Extensibility.** New cipher, key model, optimiser, or scorer drops in behind small contracts. No rewrites to join the party.
* **Robust scoring.** Start with transparent stats (unigram/bigram/wordlists). Add language models when needed — still deterministic and auditable.

### Pipeline, at a glance

```
Cipher maths  +  Key model  +  Optimiser  +  Scorer
        │             │            │            │
        └─────────────┴────────────┴────────────┘
                  run → best candidate + logs → output/…
```

* **Cipher**: transformations only (no search logic)
* **Keys**: declarative shapes (repeat/permutation/OTP/…)
* **Optimiser**: GA/SA/greedy/grid — your choice
* **Scorer**: classical first; LM‑based scorers plug in via the same interface

---

## Start here (IDE, no fuss)

1. Open `tutorials/v1/Start_Here.py` in your IDE.
2. Press **Run**.
3. Look in `output/…` for `META.json`, `logs/*.jsonl`, and `artifacts/…`.

Change one thing at a time and watch what moves.

> Prefer a command? With your venv active: `python tutorials/v1/Start_Here.py`

---

## Requirements

* **CPython 3.11** (64‑bit).
* Windows 10/11, macOS 13+, or a modern Linux distro.
* Optional: CUDA GPU + PyTorch if you want the Torch scorer.
* Optional build chain (only if rebuilding the fast LM extension): C/C++ compiler + `pybind11`.

## Installation

### Recommended (editable dev install)

Create a 3.11 virtual env in your IDE, then install the project with dev extras.

```bash
# 1) clone
git clone https://github.com/mortlach/RuneDecrypterPrime.git
cd RuneDecrypterPrime

# 2) create + activate a virtual environment
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3) install (dev extras include pytest/ruff etc.)
python -m pip install -U pip
python -m pip install -e .[dev]
```

**Skipping Torch on CPU‑only machines?**
Set `RDP_TORCH=0` before instal
