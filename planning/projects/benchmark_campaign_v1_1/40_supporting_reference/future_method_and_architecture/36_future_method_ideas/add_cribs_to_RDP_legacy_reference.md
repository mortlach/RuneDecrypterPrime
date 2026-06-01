# Hard Crib Integration for Kaeding Periodic-Columnar Solving in RuneDecrypterPrime

## Context and objective

You want to add **hard cribs** (must-match constraints) into the **Kaeding solving pipeline** for the “periodic substitution + columnar transposition” family, so that candidate plaintexts are rejected *before* expensive scoring and optimisation work continues. This is aimed at the “period 13” difficulty case you described (where lower periods work but period≈13 is sticky), and should also apply cleanly to the related compositions (periodic-only, columnar→periodic, periodic→columnar). citeturn17view2turn16view2turn43view1

At a code-architecture level, RuneDecrypterPrime (RDP) has a clear central choke-point: **all solvers evaluate candidate keys via `DecryptionProblem`, which decrypts then calls `_score_batch_texts(...)` / `_score_batch_texts_with_raw(...)`**. That makes runtime scoring the lowest-risk place to enforce “hard reject => -inf score”. citeturn4view0turn4view1turn40view0

The “reviewer-ready v0.1 schema” you drafted is compatible with RDP’s public API flow, but it cannot work as-is today because the scorer-parameter validator is strict and `ScoringConfig` will currently reject unknown keys. citeturn9view0turn10view1turn8view0

## What RDP does today

### Public API path and why “hard_crib” is currently blocked

RDP’s top-level entrypoint `RunAPI.run(...)` normalises cipher text and WLI, validates scorer parameters via `resolve_scorer_aliases(...)`, then instantiates a `ScoringConfig` dataclass with `ScoringConfig(**scorer_params)`. citeturn10view1turn21view0

Two current constraints matter:

- `resolve_scorer_aliases` explicitly raises on unknown scorer keys; its `_CANON_SCORER_KEYS` list does **not** include `hard_crib` today, so your new schema would be rejected at the API boundary. citeturn9view0  
- `ScoringConfig` (core/config/scoring.py) has a fixed set of dataclass fields; passing a new key via `ScoringConfig(**params)` would raise unless the dataclass is extended. citeturn10view1turn8view0

### Stage-2 materialisation and the runtime scoring choke-point

The Stage-2 pipeline materialises a `ProblemInstance` by building a cipher and scorer, then binding them into a `DecryptionProblem`. citeturn11view1turn13view0

`DecryptionProblem` binds ciphertext and WLI (from `CipherConfig.wli_data`) in `__post_init__`, and it is also where decrypt+score happens: `_decrypt_batch(...)` produces plaintexts, and `_score_batch_texts(...)` or `_score_batch_texts_with_raw(...)` calls the scorer. citeturn4view0turn4view1turn24view0

This is the ideal integration point because every solver (including Kaeding) ultimately evaluates candidates through this flow; the engine constructs the solver and executes it against the `ProblemInstance.problem` object. citeturn40view0turn16view2

### WLI semantics you need for word-index cribs

RDP’s WLI format is a **flat list of pairs** `[pos_in_word, word_len]` aligned 1:1 with rune positions. You detect word boundaries because `pos_in_word == word_len - 1` indicates the end-of-word (and `pos_in_word == 0` indicates the start of a word). citeturn20view0turn24view0turn23view2

This has two practical implications for hard cribs:

- Word-index constraints are feasible and deterministic because word segmentation is derived purely from WLI and is validated at config time (`CipherConfig._validate_wli_pairs`). citeturn24view0turn23view2  
- Direction matters: Runeglish encoding explicitly depends on `direction="ltr"|"rtl"` when generating rune indices and WLI. Hard-crib allowed words must therefore be encoded using the same direction as the run’s `encoding_dir`. citeturn20view0turn10view1turn28view0

## Existing “crib” facilities and the gap

RDP already contains crib-adjacent features, but they are not “hard reject” constraints:

- **Crib dragging** (tutorial + tests) uses a crib to derive key seeds and passes them through `initial_keys` into the solver, but it does not enforce that candidates must match a crib during evaluation. citeturn22view0turn22view2  
- **`WordCribConfig`** exists as a normalised structure for short-word dictionaries and per-word weighted lists (originally noted as “for bigram_sub”), but it is not wired into the periodic-columnar Kaeding solve path. citeturn14view0turn15view0turn43view1

So your agent’s key observation is correct: the periodic-columnar Kaeding path is currently driven by decrypt+score + seeded keys; crib constraints must be integrated explicitly into runtime evaluation if you want them to guide/limit Kaeding. citeturn16view2turn4view1turn43view1

## Hard crib spec aligned to RDP’s data model

### Canonical schema

Your proposed JSON is a good v0.1. The core is: **compile once, reject fast**.

A strict RDP-friendly version should be treated as part of `scorer_params` (because that is the public “knob bag” already validated and carried into Stage-2), but semantically it is a *runtime acceptance filter* over plaintext candidates, not a scoring feature. This matches your intent: “if failed in hard mode: score becomes -inf (both primary and raw paths)”. citeturn4view0turn4view1turn10view1turn9view0

### Proposed semantics mapped to RDP primitives

The rules can be expressed entirely using:

- plaintext as rune indices (`Sequence[int]`) returned by `cipher.decrypt(...)`; citeturn4view0turn17view2  
- WLI (`problem.wli_data`) which is validated to match ciphertext length and well-formed word sequences; citeturn4view0turn24view0turn23view2  
- encoding utilities (`Runeglish.encode_english_to_runes`) for compiling Latin words into rune tuples in the correct direction. citeturn20view0

Interpreting each rule:

- `per_word_allowed[i]`: “word *i* must be one of these allowed rune sequences”. Word boundaries come from WLI-derived spans. citeturn20view0turn24view0  
- `global_allowed_by_len[L]`: “every word of rune-length *L* must be in the allowed set”. Word lengths are directly available from WLI; you can derive `L` from the word span length or WLI’s `word_len`. citeturn20view0turn24view0  
- `fixed_chars[p]`: “plaintext rune at absolute position *p* must be in allowed rune-index set”. This uses plaintext positions directly and does not require WLI. citeturn4view0turn17view2  

Hard-mode scoring behaviour (RDP-aligned):

- violations return negative infinity for both primary scores and raw scores (when raw scoring is requested); RDP already centralises both paths in `_score_batch_texts` and `_score_batch_texts_with_raw`. citeturn4view0turn4view1  

WLI requirement:

- if any word-based rule is enabled and WLI is absent, the run should fail immediately; this is consistent with RDP’s own scorer behaviour when `use_word_breaks` is enabled but WLI is missing (raises). citeturn23view0turn4view0turn10view1  

## Seamless integration design in RDP

### Integration points you must touch

A minimal, coherent RDP integration needs to modify five areas that define the public-to-core path:

- `src/rune_decrypter_prime/api/_resolve.py`: allow a new scorer_params key `hard_crib` in `_CANON_SCORER_KEYS`, otherwise the public API rejects it. citeturn9view0  
- `src/rune_decrypter_prime/core/config/scoring.py`: add a `hard_crib` field to `ScoringConfig`, and normalise/validate it in `__post_init__` (so `ScoringConfig(**scorer_params)` accepts it). citeturn8view0turn10view1  
- `src/rune_decrypter_prime/core/problem/instance.py`: RDP currently constructs `DecryptionProblem(cipher=..., scorer=..., c_cfg=...)` without passing scorer params; if you want `DecryptionProblem` to compile and enforce hard cribs, `ProblemInstance.materialise(...)` needs to provide the scoring config into `DecryptionProblem` (or an equivalent mechanism). citeturn11view1turn4view0  
- `src/rune_decrypter_prime/core/problem/runtime.py`: this is the core choke-point; implement a compiled crib filter and apply it before scorer calls in `_score_batch_texts` and `_score_batch_texts_with_raw`. citeturn4view0turn4view1  
- `tools/benchmarks/bench_solve_periodic_columnar_kaeding.py`: if you add benchmark runs that use hard cribs, add a Gate-0 oracle check; note the file explicitly disables WLI during Stage-1 today, so word-based cribs would require changing that benchmark mode or limiting cribs to fixed-chars in that stage. citeturn43view1turn19view3turn10view1  

### Passing `hard_crib` into `DecryptionProblem` without destabilising the system

Today, `DecryptionProblem` does not receive `ScoringConfig` at all; it only stores `cipher`, `scorer`, and `c_cfg`. citeturn4view0turn11view1

The least invasive approach (keeps backwards compatibility with direct test construction) is:

- add an **optional** field to `DecryptionProblem`, e.g. `s_cfg: Any | None = None`, defaulting to `None`, so existing call sites that do `DecryptionProblem(cipher=..., scorer=..., c_cfg=...)` keep working (many tests construct it this way). citeturn39view0turn33view0turn29view0turn4view0  
- update `ProblemInstance.materialise` to call `DecryptionProblem(cipher=cipher, scorer=scorer, c_cfg=spec.cipher_cfg, s_cfg=spec.scorer_params)` so the runtime has access to `hard_crib` and direction. citeturn11view1turn11view0turn10view0  

This keeps the “single source of truth” for plaintext evaluation in runtime (not in solver code), which is consistent with RDP’s engine design philosophy. citeturn40view0turn4view0

### Compile-once crib filter

RDP already compiles stable runtime objects in `DecryptionProblem.__post_init__` (ciphertext, WLI coercion, keyops). That is the right place to compile hard-crib constraints once. citeturn4view0

Key precomputations:

- **Word spans** derived once from `wli_data`, using the documented `(pos_in_word, word_len)` WLI format. citeturn20view0turn24view0  
- **Allowed word sets** converted from Latin to rune-index tuples in the correct direction (from `c_cfg.encoding_dir`, which is set in wrapper cipher config construction). citeturn20view0turn28view0turn24view0  
- **Fixed-char position map** normalised into `{abs_pos: set[int]}` with rune indices bounded to `[0..28]` (Runeglish is 29-rune). citeturn20view0turn21view0  

Validation that should happen during compilation (so “fail fast” is real):

- reject empty allowed lists, non-integer indices, out-of-range rune indices; this mirrors existing strictness for WLI and scorer configuration. citeturn24view0turn9view0turn23view0  
- if any word rule is enabled and `problem.wli_data is None`, raise immediately (align with how RuneScorer raises when WLI is required but missing). citeturn23view0turn4view0  

### Runtime filtering behaviour and where to apply it

The RDP runtime scoring API has two main batch scoring entrypoints:

- `_score_batch_texts(plains_seq, wli)` for “primary only”; citeturn4view0  
- `_score_batch_texts_with_raw(plains_seq, wli, require_raw=...)` for `(pct, raw)` dual scores. citeturn4view1  

Hard cribs should be applied **before** these functions call the scorer:

- generate a boolean mask of candidates that satisfy the cribs;
- if mask is all-false: return an all-`-inf` vector (and for raw path, both vectors are all-`-inf`);
- if mask is mixed:
  - compute scores only for passing candidates (call scorer on the filtered list), then scatter the results back into the full-score arrays;
  - set failing indices to `-inf` and do not score them.

This matches your requirement (“skip scorer call” for invalid candidates) and matches RDP’s existing approach of forming arrays as `xp.asarray(..., dtype=float64)` at the runtime boundary. citeturn4view0turn4view1

### Telemetry: counters and auditability

`DecryptionProblem.__post_init__` already seeds telemetry counters such as `eval_keys`, `tokens_processed`, and `candidates_evaluated`. Extending this with crib counters is consistent with the existing telemetry bag pattern. citeturn4view0turn25view0turn27view0

A recommended minimal set (your draft is good):

- `crib_enabled` (bool) and `crib_mode` (string) for metadata;
- `crib_reject_total`, plus per-reason counters like `crib_reject_word_index`, `crib_reject_global_len`, `crib_reject_fixed_char`;
- `crib_pass_total`.

Because solution finalisation simply deep-copies `problem.telemetry` into `solution.meta["telemetry"]`, these counters will become visible in outputs without further plumbing. citeturn26view0turn27view0

## Test design with concrete RDP integration coverage

### Why tests should avoid LM assets

Many scoring tests depend on full LM assets (via guards like `require_full_lm_assets`) and are therefore heavier and not ideal for validating a runtime filter. citeturn23view0

Hard cribs can be fully validated using:

- a cipher implementation that is pure NumPy (`PeriodicSubstitutionCipher` or `PeriodicColumnarCipher`); citeturn34view0turn17view2  
- a stub scorer with deterministic outputs (`batch_score` / `batch_score_with_raw`) so you can assert “reject => -inf” regardless of scoring logic; this pattern is already used in solver tests. citeturn33view0turn39view0turn29view0  

### Validation tests you should add

The goal is to have tests that fail if any part of the “seamless integration” chain breaks: schema acceptance, compilation, enforcement, dual scoring, and batch masking.

A tight set:

- **Schema acceptance at API boundary**: ensure `resolve_scorer_aliases` accepts `hard_crib` once you add it to `_CANON_SCORER_KEYS`. citeturn9view0turn10view1  
- **`ScoringConfig` construction**: ensure `ScoringConfig(**{"hard_crib": {...}})` succeeds after adding the new field. citeturn8view0turn10view1  
- **WLI requirement**: if `per_word_allowed` or `global_allowed_by_len` is enabled but `CipherConfig.wli_data` is empty (meaning no WLI), constructing/materialising a `DecryptionProblem` should raise immediately. The WLI “empty means none” behaviour is explicit in runtime. citeturn4view0turn24view0turn23view0  
- **Known plaintext passes**: build a ciphertext from a known plaintext (encode with Runeglish so you have WLI), then ensure the true key scores finite under hard cribs. citeturn20view0turn34view0turn4view0  
- **Each rule type rejects**: create one wrong key that violates word-index crib, another that violates global-by-length crib, and another that violates a fixed-char constraint, and assert `evaluate_keys(...)` returns `-inf`. citeturn4view1turn20view0turn24view0  
- **Dual-score path**: for a stub scorer that supports raw (`batch_score_with_raw`), assert that `evaluate_keys_with_raw(...)` returns `(-inf, -inf)` for rejected candidates. RDP’s runtime explicitly supports both scoring modes. citeturn4view1turn16view2  
- **Batch masking correctness and skip-scorer contract**: pass a mixed batch `[valid_key, invalid_key, valid_key]` and assert:
  - scorer was called only for the passing candidates;
  - output array length matches batch size;
  - invalid position is `-inf`.  
  This directly tests the “filter before scoring” behaviour you want. citeturn4view0turn4view1  

Where to place tests (consistent with existing structure):

- `tests/core/test_hard_crib_runtime.py` (core-level filter behaviour using `DecryptionProblem`); patterns from other “core problem” tests apply. citeturn29view0turn39view0  
- `tests/api/test_scorer_params_hard_crib_schema.py` (validator + `ScoringConfig` construction). citeturn9view0turn8view0turn10view1  

### Determinism and regression protection

RDP has explicit determinism guard tests for `RunAPI` (“same seed + config => same result”). Hard cribs shouldn’t change random generation, but they can change solver trajectories if they prune candidates; tests should therefore focus on **deterministic behaviour given a fixed seed and fixed cribs**, not equality to previous uncribbed runs. citeturn42view0turn40view0turn16view2

A practical test is: run a small Kaeding or Beam case twice with the same seed and the same hard cribs and assert identical outputs (plaintext/key/score). This mirrors existing determinism tests, but you’ll likely want to use a stub scorer to avoid LM-asset variance. citeturn42view0turn10view1turn40view0

## Benchmark and operational guardrails

### Gate-0 oracle preflight

Your “Gate-0 benchmark preflight” recommendation is strongly aligned with how RDP benchmarks are written: the periodic-columnar Kaeding benchmark already includes sanity checks and an explicit statement that Stage-1 runs with WLI disabled. citeturn43view1turn19view0

For any benchmark run that enables hard cribs, add an early preflight:

- decrypt the oracle key to get oracle plaintext indices;
- run the crib filter against that oracle plaintext;
- if it fails, hard-abort (wrong crib should terminate the benchmark rather than burning solver budget).

This prevents the most common operational failure mode of hard cribs: an incorrect assumption that fully eliminates true solutions. It also prevents silent “everything is -inf” runs that look like solver failure but are actually crib mismatch. The need for this is especially acute in periodic-columnar where the solver is doing multi-phase moves and stage-1 already limits information (no WLI). citeturn43view1turn16view2turn17view2

### Practical note about Stage-1 WLI-off runs

Because the benchmark’s Stage-1 explicitly runs “with WLI disabled”, any word-index or global-shortword hard cribs would, by your own rule, require WLI and should fail fast if enabled. This is not a bug: it is an accurate safety property. If you want word-based hard cribs in that benchmark path, you would need to stop forcing `force_no_wli=True` for the run mode that uses them, or restrict Stage-1 cribs to `fixed_chars` only. citeturn43view1turn10view1turn4view0

### Why this integrates cleanly with Kaeding

Kaeding’s periodic-structured solver explicitly supports optimising a “raw score” path (and chooses between pct/raw for seed selection); therefore the “reject => both outputs -inf” behaviour matters, and enforcing it inside `DecryptionProblem._score_batch_texts_with_raw` is the correct place to make Kaeding behave as expected under hard cribs. citeturn16view2turn4view1turn39view0