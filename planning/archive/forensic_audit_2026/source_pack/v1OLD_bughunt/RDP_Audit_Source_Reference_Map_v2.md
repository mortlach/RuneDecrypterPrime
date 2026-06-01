# RDP Audit Source Reference Map (v2)

This file maps each ledger ID to an exact location in the two source documents.

Reference formats:

- **PDF**: `PDF p## l#-l#` refers to page + extracted line numbers in `RDP_Audit_pdf_linenum.txt`.

- **BH**: `BH L####-L####` refers to line numbers in `bug_hunt_linenum.txt`.


## PDF Open design questions (8)

- **PDF-Q01** — Canonical WLI Format — `PDF p15 l32-l35`
- **PDF-Q02** — Span vs Pos Usage — `PDF p15 l36 – p16 l2`
- **PDF-Q03** — Permutation semantics with interruptors — `PDF p16 l3-l7`
- **PDF-Q04** — Objective direction handling — `PDF p16 l8-l11`
- **PDF-Q05** — Score dtype policy — `PDF p16 l12-l16`
- **PDF-Q06** — Language model cache isolation — `PDF p16 l17-l20`
- **PDF-Q07** — user_map3 key representation — `PDF p16 l21-l25`
- **PDF-Q08** — Beam parameters source of truth — `PDF p16 l26-l28`

## PDF Findings (13)

- **PDF-01** — Objective Direction Misalignment (NEGLOGP vs Maximize) — `PDF p01 l13-l40`
- **PDF-02** — Floating-Point Precision — `PDF p02 l1-l24`
- **PDF-03** — WLI Model Activation Without WLI Data (Missing-Data Handling) — `PDF p02 l25 – p03 l13`
- **PDF-04** — Language Model Smoothing Cache Contamination — `PDF p03 l14 – p04 l3`
- **PDF-05** — Inconsistent Determinism Defaults — `PDF p04 l4-l20`
- **PDF-06** — Silent Seed Key Replacement on Normalization Failure — `PDF p04 l21 – p05 l6`
- **PDF-07** — Beam Expansion Parameter Mismatch (API vs Solver Implementation) — `PDF p05 l7-l51`
- **PDF-08** — Composite Key Length and Variable-Interruptor Handling — `PDF p06 l1 – p07 l17`
- **PDF-09** — WLI Semantic Mismatch (Start/End vs Pos/Len) — `PDF p07 l18 – p08 l14`
- **PDF-10** — WLI Span Conversion Glitch on Multi-Word Input — `PDF p08 l15 – p09 l12`
- **PDF-11** — Permutation Length Reported in Wrong Terms — `PDF p09 l13-l41`
- **PDF-12** — English Plaintext Input Ignores Specified Encoding Direction — `PDF p10 l1 – p11 l6`
- **PDF-13** — Collapsed Key Space for user_map3 (Affine Cipher) — `PDF p11 l7-l50`

## PDF Proposed integration tests (14)

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

## bug_hunt Items (59)

- **BH-B01** — WLI is two different things (and it leaks across boundaries) — `BH L1669-L1728`
- **BH-B02** — Interruptors + text permutation: alignment traps — `BH L1729-L1785`
- **BH-B03** — Periodic substitution + columnar + interruptors: round-trip invariants — `BH L1786-L1825`
- **BH-B04** — Scoring integrity (dtype honesty, batch/scalar honesty) — `BH L1826-L2296`
- **BH-S01** — Interruptor symbols are always fixed from the ciphertext (and interrupt_sym is effectively unused) — `BH L2307-L2354`
- **BH-S02** — Pool-mode interruptor search forces CompositeKeyOps (key contains interrupt positions), but scoring/WLI metadata stays global and static — `BH L2355-L2417`
- **BH-S03** — initial_text_permutation_indices is applied after interruptor removal and requires fixed core text length — variable interruptor count will crash — `BH L2418-L2471`
- **BH-S04** — InterruptorConfig exists, but key parts of it are not actually enforced/used (danger: “config looks supported” but behaviour is different) — `BH L2472-L2560`
- **BH-F2.1** — Window span maths is centralised and mostly consistent (good), but relies on a “length means X” contract — `BH L2561-L2600`
- **BH-F2.2** — NumPy backend implements WISE by injecting tags per window, and NOSE forbids boundary tags — `BH L2601-L2644`
- **BH-F2.3** — Torch backend does not support WISE at all, and its token handling differs — `BH L2645-L2693`
- **BH-F2.4** — Short-text (“no windows”) behaviour differs between NumPy and Torch when Hamming/WLI is enabled — `BH L2694-L2745`
- **BH-F2.5** — WISE “interior mean” naming/semantics look inconsistent (even before we discuss enabling WISE) — `BH L2746-L2842`
- **BH-F3.1** — Global LM table cache is writable and is expected to be mutated in-place (run-order hazard) — `BH L2855-L2898`
- **BH-F3.2** — Runtime cache keys include smoothing, but the underlying global bin cache does not (isolation is leaky) — `BH L2899-L2933`
- **BH-F3.3** — ECDF cache selection ignores window size (win), despite Bucket/meta carrying it (hidden assumption: W fixed) — `BH L2934-L2988`
- **BH-F3.4** — Cached arrays are returned by reference (accidental mutation can corrupt later results) — `BH L2989-L3020`
- **BH-F3.5** — ECDF float32 “working buffers” selection is not fully validated (q32 can lose strict increase) — `BH L3021-L3095`
- **BH-S05** — “device” semantics are inconsistent across core vs backend selection — `BH L3099-L3142`
- **BH-S06** — core runtime can materialise ciphertext as CUDA arrays even though ciphers are NumPy-only — `BH L3143-L3177`
- **BH-S07** — Score dtype “float64” is mostly a wrapper; ordering is still determined by float32 scorers — `BH L3178-L3213`
- **BH-S08** — UnifiedRuneScorer ignores the ScoringConfig.dtype intent and hard-codes float32 semantics — `BH L3214-L3246`
- **BH-S09** — Key dtype story is inconsistent (docs say uint8; core uses int16; ciphers sometimes enforce uint8) — `BH L3247-L3347`
- **BH-S10** — SolverBase early-stop state has two competing implementations + doc drift — `BH L3350-L3399`
- **BH-S11** — Improvement threshold documentation says “≥” but code uses strict “>” — `BH L3400-L3430`
- **BH-S12** — Tie-handling in top-K selection is not stable; ties can create cross-run drift — `BH L3431-L3475`
- **BH-S13** — SA acceptance and “best update” are consistent, but there is an unused knob — `BH L3476-L3512`
- **BH-S14** — Kaeding plateau logic can override plateau based on pct improvements, but telemetry state can become inconsistent — `BH L3513-L3594`
- **BH-S15** — KeyOps verb registry + capability truthfulness (base class) — `BH L3599-L3636`
- **BH-S16** — RNG API consistency (Generator vs RandomState) inside KeyOps — `BH L3637-L3662`
- **BH-S17** — GA recombination path can crash for KeyOps that don’t override recombine — `BH L3663-L3693`
- **BH-S18** — CompositeKeyOps interruptor mutation locality (repair steps can amplify a “small” move) — `BH L3694-L3746`
- **BH-S19** — “Repair to permutation” normalisation can conceal upstream key corruption — `BH L3747-L3834`
- **BH-S20** — Periodic substitution key validity is assumed (not enforced) — encryption can silently go wrong — `BH L3835-L3883`
- **BH-S21** — Columnar transposition core logic looks internally consistent for edge lengths (but batch semantics are “broadcast plaintext”) — `BH L3884-L3936`
- **BH-S22** — Pipeline “mod_keys” can hide invalid substitution keys by wrapping (worth deciding explicitly) — `BH L3937-L4008`
- **BH-S23** — Cipher pipeline composition (interruptors + text transposition/permutation + core cipher) — `BH L4010-L4072`
- **BH-S24** — TranspositionManager “perm” mode (invertibility + determinism) — `BH L4073-L4128`
- **BH-S25** — PeriodicColumnarCipher core correctness (periodic substitution + columnar transposition) — `BH L4129-L4216`
- **BH-S26** — Columnar transposition remainder handling (edge lengths) — `BH L4217-L4257`
- **BH-S27** — Interruptors + initial_text_permutation_indices interaction (length coupling) — `BH L4258-L4341`
- **BH-8A** — Seed normalisation and “default determinism” — `BH L4344-L4385`
- **BH-8B** — initial_text_permutation_indices normalisation exists but is not used — `BH L4386-L4429`
- **BH-8C** — Ciphertext index coercion can silently wrap invalid values — `BH L4430-L4468`
- **BH-8D** — Scorer param normalisation has keys that the “strict” validator will reject — `BH L4469-L4513`
- **BH-8E** — “Legacy win” is silently swallowed / conditionally merged into objective — `BH L4514-L4548`
- **BH-8F** — WLI is structurally “always there” in core configs, and scoring defaults heavily weight it — `BH L4549-L4608`
- **BH-8G** — Interruptor config precedence can silently override user intent — `BH L4609-L4696`
- **BH-S28** — initial_text_permutation_indices normalisation / validation — `BH L4697-L4739`
- **BH-S29** — Solver span duration is computed from mixed clocks — `BH L4740-L4780`
- **BH-S30** — “eval_keys” / “eval_batches” counters exist but are never updated — `BH L4781-L4812`
- **BH-S31** — Run envelope fields use setdefault and can go stale if a problem is reused — `BH L4813-L4847`
- **BH-S32** — Telemetry attachment uses setdefault and claims “shallow copy” but still shares references — `BH L4848-L4879`
- **BH-S33** — Engine records scorer impl/dtype via optional methods, so telemetry can be “unknown” even when known — `BH L4880-L4950`
- **BH-10A** — Engine seed propagation (good, but note what it guarantees) — `BH L4953-L4980`
- **BH-10B** — Legacy build_optimizer() uses entropy RNG (high-risk footgun) — `BH L4981-L5005`
- **BH-10C** — Hybrid phase RNG derivation depends on internal RNG state shape (brittle) — `BH L5006-L5040`
- **BH-10D** — Entropy RNG fallback in SolverBase seed normalisation (should not exist in a strict-deterministic framework) — `BH L5041-L5070`
- **BH-10E** — Torch determinism knobs are set globally (good intent, but device parity still needs explicit tests) — `BH L5071-L5285`
