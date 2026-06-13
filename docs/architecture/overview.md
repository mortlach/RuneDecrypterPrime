# RuneDecrypterPrime — Architecture Overview (Introductory Chapter)

*Audience:* technically minded readers who want to understand how the system is structured, why it’s built this way, and how the pieces fit together from user input to final output.

---

## 1) Purpose & Philosophy

RuneDecrypterPrime (RDP) is designed to be **transparent, modular, and deterministic**. The project favours a small number of strict, well‑named interfaces over implicit behaviour. Two guiding ideas shape everything:

1. **Two layers:** a forgiving *API layer* that accepts human‑friendly inputs and turns them into strict *core types/configs*; and a lean *engine layer* where the maths lives (ciphers, key models, search, scoring). This keeps experimentation easy without contaminating the core with ad‑hoc shortcuts.
2. **Contracts over cleverness:** enums instead of magic strings; explicit configs instead of hidden globals; reproducible randomness; and telemetry that records what actually ran. This increases trust and makes results easy to audit.

**Consequence:** New capabilities—ciphers, key models, scorers, or optimisers—drop in through narrow, documented contracts. There is a touch more boilerplate, but you gain composability, predictable behaviour, and easier debugging.

---

## 2) System at a Glance

```text
User (tutorial / script)
        │
        ▼
    API (normalisers)  ──► Core types & configs (strict enums, dataclasses)
        │                                 │
        │                                 ├──► Cipher maths (29‑rune alphabet)
        │                                 ├──► Key models (search space)
        │                                 ├──► KeyOps (mutate/recombine/constraints)
        │                                 ├──► Optimisers (SA / GA / Hybrid)
        │                                 └──► Scorers (backends: NumPy / Torch / C++)
        │                                                           │
        ▼                                                           ▼
    Run loop / pipeline  ─────────────────────────────────► Batched scoring
        │
        ▼
Best key / plaintext + telemetry (META, logs, artefacts) under `output/`
```

---

## 3) Components & Design Goals

### API Layer (forgiving front door)

* **Role:** Accept user inputs (cipher name, key hints, objective, device, budgets) in a flexible form; validate; normalise to strict core enums and config objects.
* **Why:** Keeps the core pure. The API absorbs variation in naming (e.g., `"fwd"` vs `"forward"`) and file paths, and raises clear, actionable errors.
* **Design notes:**

  * Normalisers are small and composable. They *coerce or fail*; they do not guess.
  * Public exceptions are neutral in tone and state what was received and what is valid.

### Core Types & Configs (the single source of truth)

* **Role:** Define enums (cipher, direction, device/channel, objective family, etc.) and immutable config dataclasses for cipher, scoring, and run strategies.
* **Why:** A shared vocabulary prevents subtle mismatches across modules. Enums make intent explicit and testable.
* **Design notes:**

  * Avoid `Any` in the core; prefer explicit fields with documented units/domains.
  * Defaults are deliberate and deterministic (e.g., fixed seeds unless the caller supplies one).

### Cipher Modules (the maths, nothing else)

* **Role:** Encode/decode operations over the 29‑rune alphabet. A cipher describes the transformation; it does **not** do search or scoring.
* **Why:** Clean separation allows you to test cipher correctness independently (round‑trip: encode→decode) and to reuse ciphers with different key models or scorers.
* **Design notes:**

  * Keep cipher maths pure and side‑effect free.
  * If a cipher needs tables (e.g., substitution maps), treat them as data passed in, not as hidden state.

### Key Models (what the optimiser is allowed to search)

* **Role:** Declaratively specify the structure and constraints of a key (length, alphabet, tied positions, parameter bounds, etc.).
* **Why:** The optimiser should not know cipher specifics. The key model defines the *space*, making optimisers generic and reusable.
* **Design notes:**

  * Prefer minimal models with explicit constraints (e.g., fixed positions, banned collisions) rather than bespoke logic buried in an optimiser.

### KeyOps (deterministic transformations on keys)

* **Role:** Provide the *operators* the optimiser will use to explore the key space: mutations, crossovers, neighbourhood moves, and repair/constraint functions.
* **Why this exists:** It decouples *search strategy* from *domain mechanics*. Optimisers (SA/GA/Hybrid) call KeyOps, but KeyOps know how to keep keys valid for a given model. That separation avoids duplicating domain rules inside each optimiser and makes new optimisers trivial to add.
* **Design notes:**

  * Operators are deterministic given a seeded RNG.
  * Composition is encouraged (e.g., small moves plus an occasional larger jump) and recorded in telemetry.

### Interruptors (position-only symbols)

* **Role:** Define fixed or optimizable interruptor positions as part of the key space, with a clear
  configuration surface and deterministic normalization.
* **Why:** Interruptors affect the core text and must be handled consistently across the pipeline and
  optimizers without ad-hoc branching.
* **Design notes:**

  * Default index space is absolute, pre-transposition positions.
  * Interruptor values are fixed from ciphertext (no value search in v1).
  * Search strategy (bruteforce vs KeyOps) is configurable.

See `docs/architecture/interruptors.md` for the detailed design spec.

### Optimisers (strategy, not domain)

* **Role:** Search the key space defined by the key model using KeyOps, retaining the best candidate by a scorer.
* **Why:** Different tasks prefer different strategies; keeping them generic means swapping is safe (e.g., GA for global exploration vs SA for fine‑tuning).
* **Design notes:**

  * Optimisers should accept: seeded RNG, budget (iterations/score calls), and a *batch proposal* function to enable vectorised scoring.
  * Optimisers own *when* to explore vs *when* to exploit, but never how a key is represented or validated.

### Scorers & Backends (objective, device abstraction)

* **Role:** Compute a scalar objective for candidate keys/plaintexts (e.g., language likelihood) with identical semantics across backends.
* **Why:** Scoring dominates runtime; device flexibility (CPU/GPU/C++) and batch APIs matter. A unified scorer façade hides backend differences without changing semantics.
* **Design notes:**

  * Backends should be interchangeable: NumPy as the reference, Torch/C++ as accelerators.
  * Batch interfaces first; single‑candidate scoring is layered on top for convenience.

### Wrappers & Registry (ergonomic surface)

* **Role:** Provide friendly entry points (e.g., by cipher name) and glue together cipher+key model+KeyOps bundles with sensible defaults.
* **Why:** Reduces friction for tutorials/tests and gives newcomers a safe “known‑good” path.

### Telemetry & Output (audit trail by default)

* **Role:** Persist inputs, seeds, device/backends, best key/plaintext, and run artefacts under a clean `output/` tree.
* **Why:** Reproducibility and post‑hoc analysis. The metadata tells you exactly what happened and how to reproduce it.
* **Design notes:**

  * Logs and META are compact and machine‑readable.
  * A privacy toggle can redact user/host names when sharing artefacts.

---

## 4) End‑to‑End Flow (User Input → Output)

```text
[1] User code (tutorial/script)
    └─ selects cipher, key model, objective, budgets, device
         │
[2] API normalisation
    └─ coerce names/paths → core enums/configs
         │  (fail early with clear errors if invalid)
         ▼
[3] Configuration build
    └─ freeze cipher config, scoring config, run strategy
         │
[4] Backend/device resolution
    └─ choose NumPy/Torch/C++ (semantics identical)
         │
[5] Optimiser initialisation
    └─ seeded RNG; batch proposal function; KeyOps
         │
[6] Search loop (iterate until budget)
    ├─ propose batch of candidate keys
    ├─ score batch (vectorised, backend‑specific)
    ├─ update best; adapt strategy (per optimiser)
    └─ record key events in trace/logs
         │
[7] Finalise
    ├─ emit best key/plaintext and summary
    └─ write META, logs, artefacts under `output/`
```

**Control boundaries:**

* The API validates and constructs configs; after that, the engine layer runs without consulting user input again.
* Optimisers never modify cipher maths or scoring semantics; they only explore the key space via KeyOps.
* Scorers do not know about keys—only about symbol sequences and parameters; they remain device‑agnostic behind the façade.

---

## 5) Extending the System (drop‑in patterns)

**Add a new cipher**

1. Implement pure encode/decode over runes (no side‑effects).
2. Define its key model (what a valid key looks like).
3. Provide KeyOps suited to that model (mutations/crossovers/repairs).
4. Register a wrapper so the API can expose it by name and construct defaults.

**Add a new scorer/objective**

1. Specify the objective contract (input types, shape, expected range/scale).
2. Implement NumPy reference; add Torch/C++ backends if needed with identical semantics.
3. Wire up the unified scorer façade and normalise parameters via the API.

**Add a new optimiser**

1. Implement a small interface: `propose(batch_size)`, `step(scores)`, `best()`, seeded RNG.
2. Consume KeyOps only—never embed cipher rules.
3. Emit trace hooks so runs remain explainable.

---

## 6) Design Choices & Consequences

* **Strict core, forgiving API:** reduces accidental divergence and makes behaviour stable. *Trade‑off:* slightly more boilerplate and early validation work.
* **KeyOps as a first‑class layer:** keeps domain constraints out of optimisers and encourages reuse. *Trade‑off:* requires a thin adapter when a new cipher introduces novel constraints.
* **Unified scorer façade:** stable semantics, swappable performance. *Trade‑off:* additional adapter code to align devices/dtypes.
* **Determinism by default:** easier debugging, reproducible experiments. *Trade‑off:* you must think about random seeds and log them.
* **Telemetry under `output/`:** auditability and batch analysis. *Trade‑off:* agree early on privacy toggles for shared artefacts.

---

## 7) Operational Notes (for day‑to‑day use)

* Prefer small, explicit configs in user code. Keep “what to run” in one place.
* Start with NumPy (reference semantics) before switching to a faster backend.
* Use batch scoring wherever possible; size batches to the device you have.
* Treat METADATA as part of the result: it explains *how* you got the answer.

---

## 8) Quick Glossary

* **Cipher:** the reversible maths on the 29‑rune alphabet.
* **Key model:** the structure of valid keys (what the optimiser may search).
* **KeyOps:** deterministic operators that mutate/recombine/repair keys under constraints.
* **Optimiser:** a strategy (SA/GA/Hybrid) that explores the key space via KeyOps.
* **Scorer:** computes an objective for a candidate key/plaintext; backends implement the same semantics on different devices.
* **API normalisers:** helpers that coerce human inputs to strict enums/configs and fail early when invalid.
* **Telemetry:** META, logs, and artefacts written under `output/` for audit and reproduction.

---

## 9) Minimal Worked Example (IDE‑friendly pseudocode)

```python
# 1) Choose cipher/key model/objective (friendly names are OK here)
cfg = build_config(
    cipher_name="vigenere",             # forgiving API surface
    key_model={"length": 7},            # declarative key structure
    objective="language_lm",            # scorer family
    device="auto",                      # NumPy/Torch/C++ resolved later
    budget={"iterations": 50_000},      # run strategy
    seed=1234                            # deterministic by default
)

# 2) Run the pipeline
result = run(cfg)

# 3) Inspect outputs
print(result.best_plaintext)
print(result.best_key)
# All metadata & artefacts are under output/... for audit/re-run
```

> The API accepts friendly inputs; the normalisers coerce these to core enums/configs; the run loop selects a backend, initialises an optimiser with KeyOps and a seeded RNG, scores batched candidates, and writes a reproducible record of what happened.

---

## 10) Why this structure scales

* **Local changes, global stability:** you can add a cipher or scorer without touching optimisers; add an optimiser without touching cipher maths; or switch backends without changing semantics.
* **Testability:** each layer admits focused tests—round‑trip for ciphers, property checks for KeyOps, parity tests across backends, and golden outputs for tutorials.
* **Readability:** small, explicit modules with single responsibilities are easier to review and safer to evolve.

That’s the big picture. With these contracts in place, experimentation remains fast while the core stays simple, auditable, and dependable.
