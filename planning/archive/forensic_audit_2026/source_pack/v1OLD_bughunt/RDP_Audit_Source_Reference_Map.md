# RDP Audit Source Reference Map

This file maps each ledger ID to an exact location in the two source documents.

Reference formats:

- **PDF**: `PDF p## l#-l#` refers to page + extracted line numbers in `RDP_Audit_pdf_linenum.txt`.

- **BH**: `BH L#-L#` refers to line numbers in `bug_hunt_linenum.txt`.


## PDF Findings (13)

- **PDF-01** — Objective Direction Misalignment (NEGLOGP vs Maximize) — `PDF p01 l13-l40`
- **PDF-02** — Floating-Point Precision — `PDF p02 l1-l24`
- **PDF-03** — WLI Model Activation Without WLI Data (Missing-Data Handling) — `PDF p02 l25 – p03 l13`
- **PDF-04** — Language Model Smoothing Cache Contamination — `PDF p03 l14 – p04 l3`
- **PDF-05** — Inconsistent Determinism Defaults — `PDF p04 l4-l20`
- **PDF-06** — Silent Seed Key Replacement on Normalization Failure — `PDF p04 l21 – p05 l6`
- **PDF-07** — Beam Expansion Parameter Mismatch (API vs Solver — `PDF p05 l7-l51`
- **PDF-08** — Composite Key Length and Variable-Interruptor Handling — `PDF p06 l1 – p07 l17`
- **PDF-09** — WLI Semantic Mismatch (Start/End vs Pos/Len) — `PDF p07 l18 – p08 l14`
- **PDF-10** — WLI Span Conversion Glitch on Multi-Word Input — `PDF p08 l15 – p09 l12`
- **PDF-11** — Permutation Length Reported in Wrong Terms — `PDF p09 l13-l41`
- **PDF-12** — English Plaintext Input Ignores Specified Encoding Direction — `PDF p10 l1 – p11 l6`
- **PDF-13** — Collapsed Key Space for — `PDF p11 l7-l50`

## PDF Proposed Integration Tests (14)

- **PDF-T01** — WLI Invariant Canary — `PDF p13 l10-l16`
- **PDF-T02** — WLI  vs  Runeglish  Parity — `PDF p13 l17-l22`
- **PDF-T03** — WLI  Permutation  Alignment — `PDF p13 l23-l28`
- **PDF-T04** — Objective Direction Canary — `PDF p13 l29-l34`
- **PDF-T05** — Score  Precision  Near-Tie — `PDF p13 l35 – p14 l3`
- **PDF-T06** — WLI Missing-Data Guard — `PDF p14 l4-l11`
- **PDF-T07** — Legacy vs Main Determinism — `PDF p14 l12-l17`
- **PDF-T08** — Seed Replacement Detection — `PDF p14 l18-l24`
- **PDF-T09** — test_interruptor_permutation.py — `PDF p14 l25-l31`
- **PDF-T10** — Variable  Interruptor  Count  Guard — `PDF p14 l32-l37`
- **PDF-T11** — Telemetry  Permutation  Reporting — `PDF p14 l38 – p15 l2`
- **PDF-T12** — Encoding Direction Consistency — `PDF p15 l3-l10`
- **PDF-T13** — LM  Cache  Isolation — `PDF p15 l11-l17`
- **PDF-T14** — User Map3 Full-Domain Test — `PDF p15 l18-l45`

## PDF Open Design Questions (8)

- **PDF-Q01** — Canonical WLI Format — `PDF p15 l32-l35`
- **PDF-Q02** — Span vs Pos Usage — `PDF p15 l36 – p16 l2`
- **PDF-Q03** — Permutation semantics with interruptors — `PDF p16 l3-l7`
- **PDF-Q04** — Objective direction handling — `PDF p16 l8-l11`
- **PDF-Q05** — Score dtype policy — `PDF p16 l12-l16`
- **PDF-Q06** — Language model cache isolation — `PDF p16 l17-l20`
- **PDF-Q07** — user_map3 key representation — `PDF p16 l21-l25`
- **PDF-Q08** — Beam parameters source of truth — `PDF p16 l26-l28`

## bug_hunt Headings (30)

- **BH-B01** — Block 1 — WLI is two different things (and it leaks across boundaries) — `BH L1669-L1728`
- **BH-B02** — Block 2 — Interruptors + text permutation: alignment traps — `BH L1729-L1785`
- **BH-B03** — Block 3 — Periodic substitution + columnar + interruptors: round-trip invariants — `BH L1786-L1825`
- **BH-B04** — Block 4 — Scoring integrity (dtype honesty, batch/scalar honesty) — `BH L1826-L2306`
- **BH-S01** — Subsystem 1: Interruptor symbols are always fixed from the ciphertext (and interrupt_sym is effectively unused) — `BH L2307-L2354`
- **BH-S02** — Subsystem 2: Pool-mode interruptor search forces CompositeKeyOps (key contains interrupt positions), but scoring/WLI metadata stays global and static — `BH L2355-L2417`
- **BH-S03** — Subsystem 3: initial_text_permutation_indices is applied after interruptor removal and requires fixed core text length — variable interruptor count will crash — `BH L2418-L2471`
- **BH-S04** — Subsystem 4: InterruptorConfig exists, but key parts of it are not actually enforced/used (danger: “config looks supported” but behaviour is different) — `BH L2472-L2560`
- **BH-F2.1** — Finding 2.1 — Window span maths is centralised and mostly consistent (good), but relies on a “length means X” contract — `BH L2561-L2600`
- **BH-F2.2** — Finding 2.2 — NumPy backend implements WISE by injecting tags per window, and NOSE forbids boundary tags — `BH L2601-L2644`
- **BH-F2.3** — Finding 2.3 — Torch backend does not support WISE at all, and its token handling differs — `BH L2645-L2693`
- **BH-F2.4** — Finding 2.4 — Short-text (“no windows”) behaviour differs between NumPy and Torch when Hamming/WLI is enabled — `BH L2694-L2745`
- **BH-F2.5** — Finding 2.5 — WISE “interior mean” naming/semantics look inconsistent (even before we discuss enabling WISE) — `BH L2746-L2854`
- **BH-F3.1** — Finding 3.1 — Global LM table cache is writable and is expected to be mutated in-place (run-order hazard) — `BH L2855-L2898`
- **BH-F3.2** — Finding 3.2 — Runtime cache keys include smoothing, but the underlying global bin cache does not (isolation is leaky) — `BH L2899-L2933`
- **BH-F3.3** — Finding 3.3 — ECDF cache selection ignores window size (win), despite Bucket/meta carrying it (hidden assumption: W fixed) — `BH L2934-L2988`
- **BH-F3.4** — Finding 3.4 — Cached arrays are returned by reference (accidental mutation can corrupt later results) — `BH L2989-L3020`
- **BH-F3.5** — Finding 3.5 — ECDF float32 “working buffers” selection is not fully validated (q32 can lose strict increase) — `BH L3021-L4343`
- **BH-8A** — 8A) Seed normalisation and “default determinism” — `BH L4344-L4385`
- **BH-8B** — 8B) initial_text_permutation_indices normalisation exists but is not used — `BH L4386-L4429`
- **BH-8C** — 8C) Ciphertext index coercion can silently wrap invalid values — `BH L4430-L4468`
- **BH-8D** — 8D) Scorer param normalisation has keys that the “strict” validator will reject — `BH L4469-L4513`
- **BH-8E** — 8E) “Legacy win” is silently swallowed / conditionally merged into objective — `BH L4514-L4548`
- **BH-8F** — 8F) WLI is structurally “always there” in core configs, and scoring defaults heavily weight it — `BH L4549-L4608`
- **BH-8G** — 8G) Interruptor config precedence can silently override user intent — `BH L4609-L4952`
- **BH-10A** — 10A) Engine seed propagation (good, but note what it guarantees) — `BH L4953-L4980`
- **BH-10B** — 10B) Legacy build_optimizer() uses entropy RNG (high-risk footgun) — `BH L4981-L5005`
- **BH-10C** — 10C) Hybrid phase RNG derivation depends on internal RNG state shape (brittle) — `BH L5006-L5040`
- **BH-10D** — 10D) Entropy RNG fallback in SolverBase seed normalisation (should not exist in a strict-deterministic framework) — `BH L5041-L5070`
- **BH-10E** — 10E) Torch determinism knobs are set globally (good intent, but device parity still needs explicit tests) — `BH L5071-L5285`