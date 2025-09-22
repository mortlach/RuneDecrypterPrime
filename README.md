# rune\_decrypter\_prime — Friendly Tester Preview (v0.1.0)

Welcome to **rune\_decrypter\_prime**, a modular cryptanalysis sandbox for a
29-rune alphabet. This is a **tester preview**: you can try out the basic
features before a wider release.

---

## What this project is

This project is a **cipher-solving toolkit**.
It takes text written in runes, encrypted with different classical ciphers,
and provides automated methods to recover the original message.

The framework is designed for **experimentation and learning**:
you can see how common ciphers work, and how search algorithms can be used to
crack them automatically.

---

## How it works (big picture)

The framework has four main parts:

1. **Ciphers**
   Implementations of common encryption schemes: substitution, Vigenère,
   transposition, etc.
   Each cipher has a clear API:

   * `encrypt(plaintext, key)` → ciphertext
   * `decrypt(ciphertext, key)` → plaintext

2. **Optimisers**
   Search algorithms that look for the right key. Current ones include
   **Simulated Annealing (SA)**, **Genetic Algorithm (GA)**, and a **Hybrid**
   that combines both.

3. **Scorers (Language Models)**
   Statistical models of rune text (frequencies, n-grams, etc.) that help decide
   whether a candidate plaintext “looks right.”

4. **Pipeline mixin**
   A shared component that handles tasks like consistent transposition,
   interruptor handling, and batch shaping.
   This keeps each cipher focused only on its own rules, while the shared
   pre/post-processing ensures consistency across the library.

Overall pipeline:

```
ciphertext + optimiser + scorer  →  candidate keys  →  best key  →  plaintext
```

---

## Tutorials (step by step)

All tutorials live in **`rune_decrypter_prime/examples/`**.
Each one can be run directly with Python and demonstrates a different cipher
and solving method.

---

### 1. Monoalphabetic Substitution — Simulated Annealing

**File:** `Tutorial_MonoSubstitution_SA.py`
**Method:** Starts with a random key, then makes small changes to improve it.
Occasionally worse keys are accepted to escape local traps.

* Shows score logs increasing over time.
* Final output is the recovered plaintext.

---

### 2. Monoalphabetic Substitution — Genetic Algorithm

**File:** `Tutorial_MonoSubstitution_GA.py`
**Method:** Keeps a *population* of candidate keys, combining and mutating them
across generations.

* Logs show best and average scores each round.
* Ends with a good plaintext reconstruction.

---

### 3. Monoalphabetic Substitution — Hybrid

**File:** `Tutorial_MonoSubstitution_HYBRID.py`
**Method:** Uses GA for broad exploration, then SA for fine-tuning.

* Early logs look like GA (population improving).
* Later phases switch to SA-style tweaks.
* Often finds a slightly cleaner solution than GA or SA alone.

---

### 4. Vigenère Cipher — Generic Map API

**File:** `Tutorial_Vigenere_GeneralMap.py`
**Cipher rule:** `(cipher = (plain + key) mod 29)`
**Method:** Defines the rule with the generic map API, then searches for the
right repeating key.

* Prints candidate key sequences during search.
* Final output is clear plaintext once the correct key is found.

---

### 5. Columnar Transposition

**File:** `Tutorial_ColumnarTransposition.py`
**Method:** Text is written row-by-row into a grid, then read in shuffled
column order. Solver searches for the correct order.

* Shows candidate permutations and their scores.
* Recovers the plaintext once the correct column order is found.

---

## Reproducibility tips

* Tutorials aim for **deterministic behaviour**: same inputs → same results.
  Some small variation may still occur in this preview (e.g. GA shuffling).
* To maximise reproducibility:

  * Run on CPU/NumPy.
  * Set a fixed seed in the tutorial script.
* GPU scoring (via PyTorch) is optional; it will be used if installed.
* Language models included here are trimmed n-gram sets (1-grams and 2-grams),
  enough for the demos.


Here’s how we can add that — light-hearted but still clear — at the end of the README:

## Feedback 

Since this is an early tester release, the most useful feedback is on:

* Was installation straightforward?
* Did all five tutorials run without errors?
* Were the outputs clear to understand?
* Anything confusing or missing from this README?

## What’s next

This preview only scratches the surface.
There are **lots and lots of undocumented features :)** still to come —
new ciphers, richer language models, more scoring options, and improved solver strategies.

Stay tuned for updates!

