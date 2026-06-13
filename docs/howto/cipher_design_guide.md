# Cipher Design Guide — RuneDecrypterPrime

*Audience:* technically minded newcomers and collaborators who want to understand how to approach the system, design their own ciphers, and avoid common pitfalls.

---

## 1) Orientation: the nine compartments

Think of the system as nine boxes you will touch in roughly this order. Each becomes a future GUI panel; today, each is a small config block and a few lines of code.

1. **Input** — source text and alphabet profile.
2. **Cipher** — which maths (e.g., Vigenère, Columnar, General Map).
3. **Key Model** — structure and constraints of valid keys.
4. **KeyOps** — how keys change (mutate, recombine, repair) under constraints.
5. **Objective (Scorer)** — what “good” means; semantics are identical across devices.
6. **Search Strategy (Optimiser)** — SA/GA/Hybrid; seeds and budgets.
7. **Device/Backend** — CPU (reference), GPU/accelerator (same semantics, faster).
8. **Run & Monitor** — progress, best‑so‑far, trace events.
9. **Results & Telemetry** — best key/plaintext and a reproducible audit trail under `output/`.

**Flow of control**

```text
User choices → API normalisers → Core configs
        │             │
        └── Preflight/validation (alphabet, device, budget)
                      │
            Backend selection (NumPy/Torch; same semantics)
                      │
      Optimiser + KeyOps + seeded RNG (batch proposals)
                      │
               Batched scoring (objective)
                      │
         Best key/plaintext → META/logs/artefacts
```

---

## 2) Two ways to author a cipher

You can add new capability in two complementary styles. Choose the simplest that fits your idea.

### A) **Bespoke cipher module**

Write explicit `encode`/`decode` functions over the 29‑rune alphabet. Keep them pure (no side‑effects) and test round‑trips independently. Provide a key model and matching KeyOps; register a wrapper so users can select it by name.

**When to prefer this:** the cipher has a natural, self‑contained definition (e.g., classic transpositions, block operations, or algorithms with clear inverses).

### B) **General Map (table‑driven) cipher**

Describe the cipher as a **cell rule** mapping `(p, k) → c` (symbol‑wise) with an inverse `(c, k) → p`. The cell may return a **single** output or a **small set** of candidates; encode and decode remain deterministic for a given input.

**When to prefer this:** most additive/affine/non‑linear symbol rules, or when you want to prototype unusual arithmetic quickly and reuse the same search/scoring machinery.

---

## 3) The General Map, precisely

A General Map rule is a function over the 29‑rune alphabet and (optionally) position:

```text
encode_cell(p: int, k: int, i: int) -> int | list[int]
decode_cell(c: int, k: int, i: int) -> int | list[int]
```

* **Determinism:** if the cell returns multiple candidates, the implementation uses a deterministic ordering (e.g., first/lexicographic) so runs are reproducible.
* **Bounded branching:** keep the candidate list **small** (e.g., ≤4). If a design demands higher branching, consider a beam at the pipeline level rather than unbounded cell expansion.
* **Position‑dependence:** allowed (e.g., add a term `f(i)`); document the indexing convention (0‑based; direction) in the wrapper.
* **Library functions:** you may call your own maths (e.g., modular inverses, small matrices, even ECC computations) inside the cell; the key is to produce **small, deterministic** candidate sets.

**Keys with General Map**

* **Vector keys** (length‑L, entries in `[0, 29)`): ideal for most table‑driven rules; KeyOps nudge entries ±1 and swap occasionally.
* **Tuple/Composite keys**: combine a vector with structural parameters (e.g., branch mode, per‑position caps, or a secondary vector).
* **Permutation keys**: often used alongside General Map when a layout (column order) is part of the design; keep these as a separate key component.

**What not to do**

* Do not let a cell be *empty* for valid inputs; always return at least one candidate (or have a deterministic repair path).
* Do not allow unbounded candidate lists; that causes combinatorial explosions the optimiser cannot tame.

---

## 4) The three pitfalls (remember **A–B–C**)

**A — Ambiguity Explosion**
Excessive many‑to‑one or one‑to‑many cells balloon the search space. Cap candidate counts per cell, keep a deterministic order, and consider beam strategies only when justified by the cipher.

**B — Broken Invariants / Bad KeyOps**
KeyOps must preserve constraints (e.g., permutation remains a permutation; vector entries remain mod 29), maintain **locality** (small moves, small score changes), and ensure **ergodicity** (the move set can reach the whole space). If a move violates a constraint, **repair** deterministically rather than reject; it keeps the optimiser’s “score feel” continuous.

**C — Confused Semantics**
Objectives must mean the same thing across backends; devices accelerate but never change meaning. Keep parameter names canonical in configs; avoid leaking legacy aliases at the core boundary.

---

## 5) Designing Key Models and KeyOps

**Key models** declare the search space; **KeyOps** provide the safe, deterministic ways to move within it. Typical families:

* **PermutationKey** — for columnar/transposition structures. Operators: adjacent swap, cut‑and‑insert, occasional block shuffle; always preserve bijection.
* **VectorKey(mod=29)** — for symbol‑wise rules. Operators: single‑gene ±1, small swap, occasional multi‑gene kick; clamp/wrap mod 29.
* **CompositeKey(tuple)** — for mixed designs (e.g., `(perm, vector)`). Operators act on one component at a time; combine small/local moves with a rare larger move.
* **ParametricKey** — named parameters with bounds (e.g., matrix rows/cols, state limits). Operators nudge within bounds; repairs snap back.

**Operator mix**
A healthy mix is ~90% local moves (refinement) and ~10% larger jumps (escape). All operators must be RNG‑driven but **deterministic** given the seed.

---

## 6) Blocks & Pipelines (not phase‑1 UI, but worth knowing)

Some designs are easier to express as **blocks** around the General Map:

* **Text permutation blocks** (e.g., interleave/transpose windows; index‑dependent shuffles) — pure, reversible, round‑trip tested.
* **Stateful blocks** (e.g., carry registers, feedback) — make the state explicit in the block so the cell rule remains local.
* **Pre/post transforms** (e.g., re‑indexing, rune normalisation) — keep these separate so cipher maths stays clean.

**Guideline:** keep each block’s contract tiny and testable (round‑trip where applicable). Compose blocks and the General Map to express complex ciphers without blowing up cell ambiguity.

---

## 7) How far can General Map go? (and when to abstract differently)

**Within General Map**

* **Matrix/affine rules:** expressible as `c = (a·p + b·k + d) mod 29`; put `a,b,d` in the key.
* **Non‑linear rules:** call library functions (e.g., S‑boxes, small polynomials, ECC helpers) inside the cell and output a small candidate set.
* **Position‑dependent tweaks:** add `f(i)` terms or mode flags in the key.

**When to step up a level**

* **Vector or block‑structured maths** (e.g., full matrix multiplication, long‑range coupling) is better modelled as a **block** that transforms the text (or key) before/after the General Map. This keeps the per‑cell ambiguity bounded and the search behaviour smooth.

**A clean extension vocabulary**

* **CellRule** — `(p,k,i) → candidates`; deterministic ordering; bounded size; inverse available.
* **StatefulCellRule** — additionally carries and returns a small state `(state_in → state_out)`; use sparingly.
* **Block** — transforms the text/indices (and possibly the key) as a whole; round‑trip tested; composed before or after the cell stage.

Document which layer you’re using and why; it helps readers predict performance and testability.

---

## 8) Onboarding path (what new users actually do)

1. **Hello Cipher** — run a prefilled Vigenère example; see a clean result and META.
2. **Swap & See** — same text, switch cipher or device; observe identical semantics.
3. **Strategy Showdown** — run SA vs GA with the same seed/budget; compare results.
4. **Your first composite** — Columnar ⊕ Vigenère as a one‑file exercise (composite key; two KeyOps families).
5. **Crazy but controlled** — a tiny General Map with 1–2 multi‑candidate cells; cap branching; solve a toy message.

Every example:

* runs with **seeded** RNG (reproducible),
* prints a short “what just happened”,
* writes artefacts under `output/` (safe to share).

---

## 9) Compatibility checklist (for new ciphers)

* [ ] Encode/decode are pure and deterministic for given inputs.
* [ ] For General Map, each cell returns at least one candidate; lists are **bounded** and **ordered** deterministically.
* [ ] Round‑trip holds where 1→1; expected behaviour is documented where many→1.
* [ ] Key model is explicit; KeyOps preserve invariants, maintain locality, and ensure ergodicity.
* [ ] Batch proposals exist so scoring can vectorise.
* [ ] A small smoke test solves a toy instance with a fixed seed on CPU; GPU produces the **same semantics** within FP tolerance.

---

## 10) Glossary

* **General Map:** table‑driven, symbol‑wise cipher rule over the rune alphabet.
* **Cell rule:** the `(p,k,i) → candidates` function used by General Map.
* **Key model:** declarative shape/constraints of valid keys.
* **KeyOps:** deterministic operators that move within the key space while preserving constraints.
* **Block:** a reversible, often position‑dependent transform composed before/after the cell stage.
* **Ambiguity (degeneracy):** when a cell maps to multiple candidates; must be bounded and ordered.
* **Objective (scorer):** the function producing the score; identical semantics across backends.
* **Seeded RNG:** ensures runs are reproducible end‑to‑end.

---

*Takeaway:* Start simple, prefer pure maths and bounded ambiguity, keep KeyOps local and ergodic, and use blocks to isolate structure that isn’t naturally symbol‑wise. With those habits, even very unusual ciphers become practical to prototype and solve within RDP.
