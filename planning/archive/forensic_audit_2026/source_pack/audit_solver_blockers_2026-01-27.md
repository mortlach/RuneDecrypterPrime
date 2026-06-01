# Solver-Blocking Contract Audit - 2026-01-27

Status: Active audit log (evidence-bound, no fixes yet)

Goal: Track hidden contracts that can silently block hard solves.

---

## Contract chain under test (current ground truth)

RunAPI string path:

- `RunAPI.run(...)`
- -> `normalize_ciphertext(text, wli_data)`
- -> `wli_from_text(text)` (if `text` is a string and `wli_data` is None)
- -> `coerce_wli_for_config(wli)`
- -> `CipherConfig(wli_data=...)`
- -> `DecryptionProblem.wli_data`
- -> scorer + Hamming

Key call sites:

- `src/rune_decrypter_prime/api/run.py:75`
- `src/rune_decrypter_prime/api/normalize.py:338-339`
- `src/rune_decrypter_prime/api/pipeline_helpers.py:234`
- `src/rune_decrypter_prime/core/config/cipher.py:68-71`
- `src/rune_decrypter_prime/core/problem/runtime.py:99,402`

---

## Finding 1 - WLI meaning mismatch at the API boundary

A. Observed behaviour

- `wli_from_text` emits `[word_start_offset, word_len]`, constant across a word.
- Core config docs/validation also treat WLI as start/end-like spans.
- Scoring and Hamming expect `[pos_in_word, word_len]`.

B. Implicit contract

- Any WLI that reaches scoring/Hamming must be `[pos_in_word, word_len]`.

C. Risk if violated

- Multi-word string entrypoints can mis-score and flatten ordering.
- Hamming word segmentation can break in subtle ways.

D. Evidence in code

- API construction:
  - `src/rune_decrypter_prime/api/normalize.py:279`
    - `wli.append([pos, ln])`
- API coercion into spans:
  - `src/rune_decrypter_prime/api/pipeline_helpers.py:238,244-246`
    - `needs_span_conversion = any(pair[1] < pair[0])`
    - `end = start + max(span - 1, 0)`
- Core config expects start/end:
  - `src/rune_decrypter_prime/core/config/cipher.py:68-71`
    - `wli_data items must be (start, end) pairs per docs`
- Scoring/Hamming expect pos/len:
  - `src/rune_decrypter_prime/scoring/hamming/backend.py:65`
    - `if pos == 0 and cur_r:`
  - `src/rune_decrypter_prime/scoring/hamming/Hamming.h:113`
    - `if (wli[0] == 0) {`
  - `src/rune_decrypter_prime/scoring/language_model/fastlm.cpp:206-228`
    - Token encoding packs `pos` and `len` as word-local fields.

E. Recommended stress tests

- WLI invariant on string input:
  - `normalize_ciphertext("AB CD")` should yield multiple `pos == 0` word starts,
    and always `0 <= pos < len`.
- Parity test:
  - WLI from `wli_from_text(text)` should match `Runeglish.encode_english_to_runes`
    for the same text (or fail loudly).

F. Severity

- solver-blocking (when `use_word_breaks` or Hamming are enabled)

---

## Scope note - v1 tutorials mostly avoid the string-path WLI landmine

A. Observed behaviour

- In `tutorials/v1` main runs, WLI is either:
  1) explicitly provided (usually from `Runeglish.encode_english_to_runes`), or
  2) explicitly disabled via `use_word_breaks=False` and `force_no_wli=True`.
- I do not see main tutorials calling `run(...)` with a string input and
  missing WLI while word-breaks remain enabled.

B. Implicit contract

- Tutorial success does not prove `wli_from_text` is correct; it mostly
  proves the tutorials bypass it.

C. Risk if violated

- The bug remains live for any entrypoint that passes a string without WLI
  while `use_word_breaks=True`.

D. Evidence in code

- WLI provided from the canonical encoder:
  - `tutorials/v1/Start_Here.py:32`
    - `Runeglish.encode_english_to_runes(...)`
  - `tutorials/v1/Start_Here.py:146`
    - `wli_data=demo["wli"]`
  - `tutorials/v1/Tutorial_PeriodicSubstitution.py:187`
    - `Runeglish.encode_english_to_runes(...)`
  - `tutorials/v1/Tutorial_PeriodicSubstitution.py:248`
    - `wli_data=wli`
- WLI explicitly disabled where spacing is lost:
  - `tutorials/v1/Tutorial_ColumnarTransposition.py:117`
    - `use_word_breaks: False`
  - `tutorials/v1/Tutorial_ColumnarTransposition.py:131-132`
    - `wli_data=None`, `force_no_wli=True`
  - `tutorials/v1/Tutorial_Railfence.py:84`
    - `use_word_breaks=False`
  - `tutorials/v1/Tutorial_Railfence.py:98-99`
    - `wli_data=None`, `force_no_wli=True`
- Dev tutorials still contain the landmine pattern:
  - `tutorials/v1/dev/Tutorial_Affine29.py:69-73`
    - `use_word_breaks: True` with `wli_data=None`

E. Recommended stress tests

- Tutorial-surface canary:
  - Enforce: if `text` is a string and `use_word_breaks=True`, then WLI must
    be provided or derived in a contract-valid way (pos/len).

F. Severity

- solver-degrading (dormant in main tutorials, live in other entrypoints)

---

## Finding 2 - WLI/text permutation alignment is not enforced

A. Observed behaviour

- Text permutations are applied to tokens.
- I see no corresponding WLI permutation before scoring.

B. Implicit contract

- If tokens are permuted, WLI must be permuted identically before scoring.

C. Risk if violated

- Even correct WLI becomes misaligned under permutations, corrupting WLI features.

D. Evidence in code

- Text permutation:
  - `src/rune_decrypter_prime/utils/transposition.py:43-47`
    - `return arr[self._text_perm]`
- WLI passed through untouched to scoring:
  - `src/rune_decrypter_prime/core/problem/runtime.py:99,402`
    - WLI stored once and reused for scoring.

E. Recommended stress tests

- Permutation alignment test:
  - With `initial_text_permutation_indices` and `use_word_breaks=True`,
    scoring should match a reference path that permutes both text and WLI.

F. Severity

- solver-degrading (can become solver-blocking on hard WLI-weighted runs)

---

## Finding 3 - WLI semantic/range validation is missing at runtime

A. Observed behaviour

- WLI is coerced to `uint8` with no semantic validation.
- WLI pos/len are masked to 6 bits in the hashing pipeline.

B. Implicit contract

- WLI values must satisfy `0 <= pos < len <= 63`, or the hash space is corrupted.

C. Risk if violated

- Positions and lengths can wrap or collide silently, destroying WLI gradients.

D. Evidence in code

- Coerce to uint8 without semantic checks:
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:47,50`
    - `np.asarray(..., dtype=np.uint8)`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:480,486`
    - `np.asarray(pairs, dtype=np.uint8)` and stack
- Hot path bypasses the strict validator:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:488,491-493`
    - `mdl = self.lm._ensure(...)`
    - `mdl.batch_logp(..., wli, ...)`
- 6-bit masking:
  - `src/rune_decrypter_prime/scoring/language_model/fastlm.cpp:227-228`
    - `(pos & 0x3F)` and `(len & 0x3F)`
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:424-425`
    - `pos = (w_win[..., 0] & 0x3F)`, `ln = (w_win[..., 1] & 0x3F)`
- The strict validator exists but is not on the hot path:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:396-397`
    - `0 <= pos < L <= 63`

E. Recommended stress tests

- WLI contract canary:
  - Assert that every WLI reaching scoring satisfies `0 <= pos < len <= 63`.
- Adversarial wrap test:
  - Feed a WLI with `pos >= 64` and assert a hard failure instead of silent wrap.

F. Severity

- solver-blocking (for WLI-heavy hard problems)

---

## Finding 4 - Objective direction is an implicit, unsafe contract

A. Observed behaviour

- `ScoringConfig.maximize` exists but is not enforced by solvers.
- Solvers assume higher-is-better.
- `NEGLOGP` returns `-avg_logp`, which is directionally unsafe under that assumption.

B. Implicit contract

- Every objective used with these solvers must be maximize-compatible.

C. Risk if violated

- The solver can optimize in the wrong direction while telemetry looks reasonable.

D. Evidence in code

- Maximize flag exists:
  - `src/rune_decrypter_prime/core/config/scoring.py:66`
    - `maximize: bool = True`
- Solvers use `>` and descending sorts:
  - `src/rune_decrypter_prime/solvers/solver_base.py:458-459`
    - `if current_best > (self._best_score_so_far + self.plateau_min_delta):`
  - `src/rune_decrypter_prime/solvers/solver_base.py:1088-1089`
    - `best_score >= stop_score`
  - `src/rune_decrypter_prime/solvers/beam.py:129`
    - `np.argsort(scores)[-parents:][::-1]`
  - `src/rune_decrypter_prime/solvers/ga.py:209`
    - `order = np.argsort(scores)[::-1]`
- NEGLOGP sign:
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:1128`
    - `return float(-np.asarray(bucket_out["avg"]["logp"], dtype=np.float32)[0])`

E. Recommended stress tests

- Objective direction canary:
  - Construct two controlled scores `s_bad < s_good` and assert each solver treats
    `s_good` as better.
- NEGLOGP guardrail:
  - If `ObjectiveFamily.NEGLOGP` is selected, assert a hard failure unless a solver
    explicitly declares it can minimize.

F. Severity

- solver-blocking (if NEGLOGP is ever used in live runs)

---

## Finding 5 - dtype knob is not honored in the optimization path

A. Observed behaviour

- ECDF interpolation forces float32.
- NumPy batch scoring stores results in float32.

B. Implicit contract

- If dtype is configurable, it must change the decision precision where solvers compare scores.

C. Risk if violated

- Near-tie improvements can collapse, causing plateaus and misleading tuning.

D. Evidence in code

- ECDF interpolation casts to float32:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:238,248`
    - `x_arr = np.asarray(x, dtype=np.float32)`
    - `return out.astype(np.float32, copy=False)`
- Batch scoring stores float32:
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:853`
    - `out = np.zeros((len(pts),), dtype=np.float32)`

E. Recommended stress tests

- Scalar vs batch near-tie parity:
  - Assert ordering is preserved for two near-tie candidates.
- dtype honesty:
  - `dtype="float64"` should change at least some scores in an adversarial ECDF case.

F. Severity

- solver-blocking on hard problems with tiny score deltas

---

## Finding 6 - WLI presence is not part of model activation or renormalization

A. Observed behaviour

- Model activation uses config flags, not actual WLI presence.
- When WLI is absent but `use_word_breaks=True`, WLI models are still
  included in weight normalization, then silently skipped during scoring.
- If `include_char=False` and WLI is absent, scores can collapse toward
  a constant floor without a hard failure.

B. Implicit contract

- WLI-weighted models must only be active when valid WLI is present,
  or the scorer must fail loudly and early.

C. Risk if violated

- Solver-degrading in mixed models (scale shifts and misleading stop/min_delta).
- Solver-blocking in WLI-only configs where missing WLI yields near-constant
  scores and flat gradients.

D. Evidence in code

- NumPy path activates models without checking WLI presence:
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:349`
    - `models = self._active_models()`
- NumPy path silently skips WLI but keeps normalized weights:
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:454`
    - `if wli_w_map is None or wli_w_map.get(int(n)) is None:`
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:487`
    - `pct_perwin += np.float32(w) * u`
- Torch path has the same gating mismatch:
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:447,775`
    - `models = self._active_models(self.use_wli)`
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:510-511,833-834`
    - `wli_t = None` unless `wli_b is not None`
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:526-527,843-844`
    - `if toks is None: continue`

E. Recommended stress tests

- WLI-missing hard guard:
  - With `include_char=False`, `use_word_breaks=True`, and `wli=None`,
    scoring should raise a clear error rather than return a constant-ish score.
- Renormalization honesty:
  - With `include_char=True` and `use_word_breaks=True`, compare scores
    between:
    1) missing WLI, and
    2) present WLI with all WLI weights forced to 0.
  - These two cases should match closely, or the scorer should report
    that WLI was requested but unavailable.

F. Severity

- solver-blocking (WLI-only configs), solver-degrading otherwise

---

## Finding 7 - Determinism contract differs between main and legacy entrypoints

A. Observed behaviour

- The main pipeline forces a deterministic default seed of 0.
- The legacy solver engine falls back to entropy when no RNG is supplied.

B. Implicit contract

- "Same inputs, same outputs" determinism should not depend on which entrypoint
  you used.

C. Risk if violated

- Solver-degrading for debugging and audits: hard problems can look flaky or
  irreproducible when exercised through legacy paths.

D. Evidence in code

- Main pipeline enforces seed 0 when unspecified:
  - `src/rune_decrypter_prime/api/pipeline.py:103-105`
    - `if effective_seed is None: effective_seed = 0`
- Engine RNG is then deterministic:
  - `src/rune_decrypter_prime/core/engine/engine.py:60-62`
    - `s = 0 if seed is None else int(seed)`
    - `np.random.default_rng(s)`
- Legacy path uses entropy when RNG is not injected:
  - `src/rune_decrypter_prime/core/solver_engine.py:74`
    - `rng = np.random.default_rng()`

E. Recommended stress tests

- Legacy determinism canary:
  - Exercise the legacy solver-engine entrypoint twice with the same inputs
    and no explicit seed; assert it either fails loudly or is deterministic.

F. Severity

- solver-degrading

---

## Finding 8 - Unified scorer forces float32 batch outputs

A. Observed behaviour

- The unified scorer wrapper casts batch outputs to float32 unconditionally,
  regardless of backend or requested dtype policy.

B. Implicit contract

- Decision precision at the solver boundary should not be silently reduced
  by an adapter layer.

C. Risk if violated

- Solver-degrading on hard problems: near-tie improvements can collapse
  even if a backend computes higher-precision scores.

D. Evidence in code

- Unified scorer batch cast:
  - `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:55-56`
    - `return np.asarray(self._backend.batch_score(pts, wlis), dtype=np.float32)`
- Unified scorer raw fallback also casts:
  - `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:64`
    - `pct = np.asarray(self._backend.batch_score(pts, wlis), dtype=np.float32)`

E. Recommended stress tests

- Adapter precision canary:
  - With a backend that returns float64 batch scores, assert that the unified
    adapter preserves dtype and ordering (or fails loudly).

F. Severity

- solver-degrading

---

## Finding 9 - Initial permutation is incompatible with interruptors in the main pipeline

A. Observed behaviour

- The API passes `initial_text_permutation_indices` into `ProblemSpec.input_permutation`,
  which is validated against the full ciphertext length.
- Interruptors are removed before the permutation is applied.
- The transposition manager enforces that the permutation length matches the
  post-removal core length.
- The cipher pipeline documentation states the permutation is over indices
  after interruptor removal.

B. Implicit contract

- If interruptors are present, a valid initial permutation must be defined in
  the same index space and length as the core text after interruptor removal.

C. Risk if violated

- Solver-blocking: a full-length permutation can pass early validation but
  fail at runtime as soon as interruptors remove any tokens.
- The converse is also blocked: a core-length permutation would be rejected
  by the full-length validation step.

D. Evidence in code

- API forwards the same permutation into the spec:
  - `src/rune_decrypter_prime/api/pipeline.py:74`
    - `input_permutation=initial_text_permutation_indices`
- Spec validation enforces full ciphertext length:
  - `src/rune_decrypter_prime/core/problem/instance.py:22`
    - `input_permutation must have length {n}`
- Interruptor removal happens before applying the permutation:
  - `src/rune_decrypter_prime/core/problem/runtime.py:730`
    - `ct_core, info = cipher._intr_mgr.remove_from(...)`
  - `src/rune_decrypter_prime/core/problem/runtime.py:734`
    - `ct_tr = cipher._trans_mgr.apply_text(ct_core)`
- Transposition manager requires a length match at application time:
  - `src/rune_decrypter_prime/utils/transposition.py:45`
    - `raise ValueError("text_perm must match text length")`
- Cipher pipeline docs define the permutation in core space:
  - `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:94`
    - `indices after interrupter removal`

E. Recommended stress tests

- Interruptor + permutation contract canary:
  - Configure `interruptors_exact=[1]` and set a full-length permutation.
  - Assert the pipeline fails early with a clear contract error (not a late
    `text_perm must match text length`).
- Dual-canary:
  - Attempt a core-length permutation with interruptors present and assert the
    system either accepts it explicitly or fails with a message that references
    core-length semantics.

F. Severity

- solver-blocking (for any attempt to combine interruptors with initial permutation)

---

## Finding 10 - Variable interruptor counts are structurally incompatible with fixed permutations

A. Observed behaviour

- Composite interruptor keyops can vary the number of interruptors between
  `min_count` and `max_count` using sentinels.
- The core length changes with the interruptor count.
- The initial permutation is fixed-length and is enforced at application time.

B. Implicit contract

- A fixed permutation can only be valid if the core length is constant across
  all evaluated keys (i.e., interruptor count must be fixed).

C. Risk if violated

- Solver-blocking: runs can crash mid-search when the interruptor count for a
  candidate key changes the core length away from the permutation length.

D. Evidence in code

- Variable interruptor counts are explicitly sampled and mutated:
  - `src/rune_decrypter_prime/keyops/composite.py:306`
    - `count = int(_rng_integers(rng, self.interrupt_min, self.interrupt_K + 1))`
  - `src/rune_decrypter_prime/keyops/composite.py:334`
    - `intr[slot] = self.sentinel`
- The permutation is applied after removal for each key:
  - `src/rune_decrypter_prime/core/problem/runtime.py:734`
    - `ct_tr = cipher._trans_mgr.apply_text(ct_core)`
- Application enforces a length match:
  - `src/rune_decrypter_prime/utils/transposition.py:45`
    - `text_perm must match text length`

E. Recommended stress tests

- Count-variation canary:
  - Use `InterruptorConfig(mode="pool", min_count=0, max_count=2)` and an
    initial permutation.
  - Evaluate two keys with different interruptor counts and assert the system
    fails loudly with a count/permutation contract error.

F. Severity

- solver-blocking (when variable-count interruptors and permutations coexist)

---

## Finding 11 - Pipeline telemetry encodes permutation length in the wrong index space

A. Observed behaviour

- The pipeline block summary always uses the full ciphertext length as the
  permutation length, regardless of interruptor removal semantics.
- The cipher pipeline defines initial permutations in core space after
  interruptor removal.

B. Implicit contract

- Telemetry must use the same index space/length semantics as the runtime,
  or it becomes misleading during debugging and regression tracking.

C. Risk if violated

- Solver-degrading: telemetry can appear consistent while the underlying
  permutation contract is violated (or impossible to satisfy).

D. Evidence in code

- Telemetry uses ciphertext length directly:
  - `src/rune_decrypter_prime/telemetry/pipeline.py:79`
    - `perm_info = _perm_summary(text_permutation, int(ciphertext_len))`
- The permutation is validated against the full length:
  - `src/rune_decrypter_prime/core/problem/instance.py:22`
    - `input_permutation must have length {n}`
- Cipher pipeline states core-space semantics:
  - `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:94`
    - `indices after interrupter removal`

E. Recommended stress tests

- Telemetry index-space canary:
  - With interruptors enabled, assert that any reported permutation length/hash
    is explicitly tied to either full-text or core-text semantics (and that the
    same semantics are enforced at runtime).

F. Severity

- solver-degrading (telemetry can lie about the true contract)

---

## Finding 16 - English string input ignores encoding direction while scoring still uses it

A. Observed behaviour

- `RunAPI.run()` normalises `encoding_dir` but does not pass it into
  ciphertext/WLI normalisation.
- `normalize_ciphertext()` calls `to_indices(text)` with no direction.
- The English-string path in `to_indices()` transliterates per word but does
  not consider `encoding_dir`.
- Scoring config *does* receive `encoding_dir`, so the runtime can score RTL
  assets against LTR-encoded indices when the input is English text.

B. Implicit contract

- If direction is part of the representation contract, direction-sensitive
  transliteration must happen before direction-sensitive scoring is selected.

C. Risk if violated

- Solver-degrading (and sometimes solver-blocking) on direction-sensitive runs:
  the scorer can use RTL assets while the input was encoded LTR, producing
  misleading gradients and tuning signals.

D. Evidence in code

- Direction is normalised but not used in normalisation:
  - `src/rune_decrypter_prime/api/run.py:RunAPI.run`
    - `encoding_dir = normalize_encoding_dir(encoding_dir)`
    - `ct, wli = normalize_ciphertext(text, wli_data)`
- Normalisation does not accept direction:
  - `src/rune_decrypter_prime/api/normalize.py:normalize_ciphertext`
    - `ct = to_indices(text)`
- English-string transliteration is directionless:
  - `src/rune_decrypter_prime/api/normalize.py:to_indices`
    - `rw = Runeglish.translate_to_gematria(w.upper())`
- Scoring direction is set from `encoding_dir`:
  - `src/rune_decrypter_prime/api/run.py:RunAPI.run`
    - `scoring_cfg.encoding_dir = encoding_dir`

E. Recommended stress tests

- Direction canary for English string input:
  - Provide an English string and run twice with `encoding_dir="ltr"` and
    `encoding_dir="rtl"`.
  - Assert that the *encoded indices* differ when direction differs, or fail
    loudly if string inputs are not direction-aware.
- API-vs-Runeglish parity test:
  - Compare the API string path against
    `Runeglish.encode_english_to_runes(text, direction=...)` for both LTR and
    RTL, and require index parity.

F. Severity

- solver-degrading (becomes solver-blocking on direction-sensitive problems)

---

## Finding 17 - Legacy solver engine RNG defaults to entropy, bypassing deterministic defaults

A. Observed behaviour

- The Stage-2 engine defaults to `seed=0` when no seed is provided.
- The legacy `build_optimizer(...)` helper creates a fresh RNG with
  `np.random.default_rng()` when `rng` is not supplied, which uses entropy.

B. Implicit contract

- Determinism defaults should be consistent across entrypoints, especially for
  debugging hard-solve plateaus.

C. Risk if violated

- Solver-degrading for reproducibility: runs that go through the legacy helper
  can drift run-to-run even when the "same config" is used elsewhere.

D. Evidence in code

- Deterministic default in the Stage-2 pipeline:
  - `src/rune_decrypter_prime/api/pipeline.py:execute_run`
    - `if effective_seed is None: effective_seed = 0`
- Entropy default in the legacy helper:
  - `src/rune_decrypter_prime/core/solver_engine.py:build_optimizer`
    - `if rng is None: rng = np.random.default_rng()`

E. Recommended stress tests

- Legacy determinism canary:
  - Call `build_optimizer(problem, cfg, rng=None)` twice and assert that the
    chosen first key and first scores match exactly; if not, fail loudly with
    a determinism contract error.

F. Severity

- solver-degrading (reproducibility and debugging risk)

---

## Finding 18 - RTL direction alters tokenisation, not just token order (cannot verify intended contract)

A. Observed behaviour

- In `Runeglish.encode_english_to_runes`, RTL reverses the raw string before
  tokenisation, then reverses the token list after tokenisation.
- Because tokenisation is greedy and sensitive to bigrams/trigrams, reversing
  before tokenisation can change which tokens are detected.

B. Implicit contract

- If RTL is intended to mean "reverse the token sequence within each word
  after normal tokenisation," then tokenisation must be performed on the
  original word before any reversal.

C. Risk if violated

- Solver-degrading in direction-sensitive pipelines: direction becomes a
  representational change, not just an ordering change, which can leak across
  data building, scoring, and solver expectations.

D. Evidence in code

- RTL reverses before and after tokenisation:
  - `src/rune_decrypter_prime/utils/runeglish.py:encode_english_to_runes`
    - `if direction.lower() == "rtl": raw = raw[::-1]`
    - `if direction.lower() == "rtl": tokens.reverse()`

E. Recommended stress tests

- RTL semantics canary:
  - Encode a word containing a known trigram/bigram (e.g., "ING", "THE") in
    LTR, then reverse the token list.
  - Compare to the RTL encoding and assert equality; fail loudly if they differ.

F. Severity

- performance-sensitive / solver-degrading (cannot verify intended contract from provided files)

---

## Finding 12 - WLI inference + span conversion can explode WLI lengths on multi-word string input

A. Observed behaviour

- The API infers WLI from strings via `wli_from_text()`, which emits
  `[word_start_offset, word_len]` pairs (constant across a word).
- The pipeline then runs `coerce_wli_for_config()`, which flips into a
  "span conversion" mode if it sees any pair where `second < first`.
- For multi-word input, `word_start_offset` quickly exceeds `word_len`,
  so span conversion is triggered and the second value becomes a large
  end-position-like number.
- Scoring backends treat the second value as `word_len` and silently mask
  both `pos` and `len` to 6 bits.

B. Implicit contract

- Any WLI that reaches scoring must be `[pos_in_word, word_len]` with
  `0 <= pos < word_len <= 63`.
- WLI inference and reconciliation must not change semantic meaning based
  on the observed values.

C. Risk if violated

- Solver-blocking on string-path runs: large "lengths" get truncated by the
  6-bit mask, causing heavy hash collisions and flattened gradients.
- Telemetry can look reasonable while the WLI channel is effectively corrupted.

D. Evidence in code

- WLI inference uses word-start offsets:
  - `src/rune_decrypter_prime/api/normalize.py:wli_from_text`
    - `wli.append([pos, ln])`
    - `pos += ln`
- Span conversion triggers on any `second < first`:
  - `src/rune_decrypter_prime/api/pipeline_helpers.py:coerce_wli_for_config`
    - `needs_span_conversion = any(int(pair[1]) < int(pair[0]) for pair in wli ...)`
    - `end = start + max(span - 1, 0)`
- The API always applies this coercion:
  - `src/rune_decrypter_prime/api/pipeline.py:execute_run`
    - `wli=coerce_wli_for_config(wli)`
- Scoring masks WLI to 6 bits:
  - `src/rune_decrypter_prime/scoring/language_model/fastlm.cpp`
    - `(uint32_t(pos & 0x3F)<<5) | (uint32_t(len & 0x3F)<<11)`
- The intended WLI contract is pos/len bounded by 63:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:_validate`
    - `if not (0 <= pos < L <= 63):`

E. Recommended stress tests

- Multi-word string WLI invariant canary:
  - Call the public API with a multi-word rune or English string and no
    `wli_data`.
  - Assert every WLI pair satisfies `0 <= pos < len <= 63`.
- String-path parity vs Runeglish:
  - Compare inferred WLI from the API string path against
    `Runeglish.encode_english_to_runes(...)[1]` on the same text.
  - Require exact equality of the WLI pairs.

F. Severity

- solver-blocking (for any pipeline path that relies on string WLI inference)

---

## Finding 13 - Tests and docs encode start-offset WLI semantics, masking scorer contracts

A. Observed behaviour

- API docs and tests explicitly describe WLI as `[start, length]` and
  assert that `wli_from_text()` returns `[0, L]` for every rune in a word.
- Meanwhile, scoring and rendering logic clearly expect
  `[pos_in_word, word_len]`.

B. Implicit contract

- The test suite must enforce the same WLI meaning that scoring and hamming
  require: `[pos_in_word, word_len]`.

C. Risk if violated

- Solver-degrading and potentially solver-blocking: a broken WLI construction
  can pass tests, then silently corrupt the WLI channel at runtime.
- Contract drift becomes hard to detect because the wrong behaviour is
  "blessed" by tests.

D. Evidence in code

- Tests assert the start-offset form:
  - `tests/api/test_normalize.py:test_make_single_word_wli_and_wli_from_text`
    - `assert rune_wli == [[0, 2], [0, 2]]`
- API docs describe start/length:
  - `src/rune_decrypter_prime/api/normalize.py:make_single_word_wli`
    - `WLI is *always* a list of [start, length] pairs (v1 contract).`
  - `src/rune_decrypter_prime/api/normalize.py:wli_from_text`
    - `Each rune of a word shares that word's [start, length].`
- Scoring expects position-in-word:
  - `src/rune_decrypter_prime/utils/runeglish.py:encode_english_to_runes`
    - `wli_out.extend([[j, m] for j in range(m)])`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:_validate`
    - `0 <= pos < L <= 63`
  - `src/rune_decrypter_prime/scoring/hamming/Hamming.h:create_word_data`
    - `if (wli[0] == 0) {  // start of a word`

E. Recommended stress tests

- WLI semantics contract test:
  - For a two-rune word, assert inferred WLI is `[[0, 2], [1, 2]]`, not
    `[[0, 2], [0, 2]]`.
- WLI semantics cross-check:
  - For multi-word text, assert multiple word starts appear as repeated
    `pos == 0` positions inside a fixed word length, not via large offsets.

F. Severity

- solver-degrading (and solver-blocking on any string-inference path)

---

## Finding 14 - Invalid seeds can be silently replaced with random keys

A. Observed behaviour

- Seed keys are normalized in `SolverBase.__init__`.
- If normalization fails for a seed row, the solver logs a debug message and
  replaces that seed with `keyops.random(rng)`.
- Only seeds that fail both normalization and random replacement are counted
  as "dropped" in seed diagnostics.

B. Implicit contract

- Provided seeds must either:
  - normalize successfully, or
  - trigger a loud error / explicit telemetry flag when replaced.
- Seed keys must match the full `keyops.caps.length`, which is larger than
  the core key length when using composite interruptors.

C. Risk if violated

- Solver-degrading: seeded runs can silently become random-start runs.
- Tuning and debugging become misleading because telemetry still reports
  `seed_keys_count` and `seed_source="provided"` even when seeds were replaced.

D. Evidence in code

- Normalization fallback replaces seeds with random keys:
  - `src/rune_decrypter_prime/solvers/solver_base.py:211`
    - `self.keyops.normalize(row)`
  - `src/rune_decrypter_prime/solvers/solver_base.py:223`
    - `replacement = np.asarray(self.keyops.random(rng_fallback), dtype=self.key_dtype)`
- Composite keyops require the full composite length:
  - `src/rune_decrypter_prime/keyops/composite.py:_split`
    - `Composite key length {arr.size} != {self.core_K + self.interrupt_K}`
- Seeds are passed straight into the engine:
  - `src/rune_decrypter_prime/api/pipeline.py:execute_run`
    - `seed_keys=(np.asarray(initial_keys, dtype=KEY_DTYPE) if initial_keys is not None else None)`

E. Recommended stress tests

- Seed replacement canary:
  - Provide seeds with the wrong length for composite keyops and assert the
    run either fails loudly or emits a telemetry flag like
    `seed_diag.seed_normalize_replaced > 0`.
- Seed preservation test:
  - Provide valid seeds and assert the normalized seeds match the original
    seeds exactly (or by a documented normalization rule).

F. Severity

- solver-degrading

---

## Finding 15 - Interruptor pools are not validated against ciphertext length until evaluation

A. Observed behaviour

- Interruptor pools are validated for type, non-negativity, and uniqueness,
  but not against the ciphertext length.
- The first time pool values are checked against ciphertext length is during
  decrypt/evaluate, via `_validate_interrupt_idx(...)`.

B. Implicit contract

- Interruptor pools must be within `[0, ciphertext_len)` and should be
  validated at problem materialization time, not mid-solve.

C. Risk if violated

- Solver-blocking: a run can crash during evaluation after the solver has
  already started.
- Debugging is harder because the failure is delayed and solver-dependent.

D. Evidence in code

- Interruptor config validates only non-negative and uniqueness:
  - `src/rune_decrypter_prime/core/config/interruptor.py:_coerce_indices`
    - `if val < 0: raise ValueError(...)`
    - `if len(set(out)) != len(out): raise ValueError(...)`
- Composite keyops validate pool shape/content, not ciphertext length:
  - `src/rune_decrypter_prime/keyops/composite.py:__init__`
    - `if (pool < 0).any(): raise ValueError(...)`
- Range validation happens only at evaluation time:
  - `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:_validate_interrupt_idx`
    - `if (idx < 0).any() or (idx >= length).any(): raise ValueError(...)`
  - `src/rune_decrypter_prime/core/problem/runtime.py:_prepare_candidate_inputs`
    - `cipher._validate_interrupt_idx(idx, int(ct_idx.size))`

E. Recommended stress tests

- Out-of-range pool canary:
  - Provide `InterruptorConfig(mode="pool", pool=[len(ciphertext)])`.
  - Assert a clear, early error before solver start.
- Pool-length contract test:
  - Assert that problem materialization validates interruptor pools against
    ciphertext length.

F. Severity

- solver-blocking (for invalid interruptor pool configurations)

---

## Tests that would catch most of the above quickly

1) WLI invariant canary at scoring boundary:
   - Detects contract drift and silent wraps.
2) WLI string-path parity vs Runeglish:
   - Detects wrong WLI construction.
3) WLI + permutation alignment test:
   - Detects misalignment under `initial_text_permutation_indices`.
4) Objective direction canary:
   - Detects sign/ordering mismatches.
5) Scalar vs batch near-tie ordering test:
   - Detects quantization-induced rank inversions.
6) WLI-missing gating/renormalization test:
   - Detects silent WLI model activation when WLI is unavailable.
7) Legacy determinism canary:
   - Detects entropy-based RNG drift outside the main pipeline.

---

## Open questions to resolve before fixes

1) Canonical WLI meaning:
   - Should WLI be strictly `[pos_in_word, word_len]` everywhere?
2) Start/end spans:
   - Are `(start, end)` pairs required anywhere, or are they legacy noise?
3) Permutation semantics:
   - When applying `initial_text_permutation_indices`, should WLI be permuted
     in lockstep?
4) Objective direction policy:
   - Do we want to ban NEGLOGP at runtime, or add a minimize-aware solver mode?
5) dtype policy:
   - Is `dtype="float64"` intended to affect decision precision on CPU only?

---

## Finding 19 - LM smoothing/OOV settings can leak across scorers via a path-only cache

A. Observed behaviour

- Joint LM tables are cached by absolute path only.
- The native LM model recomputes/smooths `logp` in-place on the provided buffer.
- Changing smoothing/OOV settings in one scorer can therefore mutate the shared
  cached arrays used by another scorer in the same process.

B. Implicit contract

- Smoothing/OOV configuration must be either:
  1) process-global and immutable, or
  2) isolated per scorer/runtime instance.

C. Risk if violated

- Solver-degrading and audit-hostile: scoring behaviour can change mid-run (or
  between runs in the same process) without any telemetry signal.
- Hard-problem tuning becomes misleading because the objective surface itself
  can drift as other scorers are constructed.

D. Evidence in code

- Path-only cache with explicitly writable arrays:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:_load_bin`
    - `_load_bin_cache: dict[Path, tuple[np.ndarray, ...]] = {}`
    - `if path in _load_bin_cache: return _load_bin_cache[path]`
    - "native scorer may update `logp` when applying smoothing"
- Smoothing happens in-place in the native model:
  - `src/rune_decrypter_prime/scoring/language_model/fastlm.cpp:FastTransitionModel`
    - `logp_arr;   // overwritten with smoothed values`
    - `logp_ptr[i] = lp;`
- The smoothing parameters are injected at model construction time:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:LanguageModelPrime._ensure`
    - `keys, logp, cnts, mask = _load_bin(path)`
    - `_fastlm.FastTransitionModel(... self._smooth_mode, self._alpha, self._oov_mode ...)`

E. Recommended stress tests

- Cross-instance contamination canary (single process):
  - Construct scorer A with `smoothing="none"` and score a fixed input.
  - Construct scorer B with `smoothing="auto_gt"` (same assets), then rescore
    with scorer A.
  - A's score should remain identical; any drift indicates cache contamination.

F. Severity

- solver-degrading (can become solver-blocking for rigorous audits and hard tuning)

---

## Finding 20 - `user_map3` key-space is silently collapsed to `A` (k1 dimension unreachable)

A. Observed behaviour

- `user_map3` is defined over a key-value domain of size `A*A`.
- The cipher pipeline mod-reduces keys by `self.A` (e.g., 29) before decrypt.
- KeyOps hints for generic maps are derived from `cipher.A`, not `A*A`.
- As a result, solver-generated keys appear limited to `0..A-1`, which cannot
  encode `k1 > 0` in the `A*A` domain.

B. Implicit contract

- For `user_map3`, the runtime must either:
  1) operate over the full `A*A` key-value domain, or
  2) model two key streams explicitly and never mod-reduce the encoded pair.

C. Risk if violated

- Solver-blocking for `user_map3`/affine-like ciphers: the solver cannot explore
  most of the key space even though the cipher tables were built for it.
- Telemetry can still look plausible while the solver is effectively trapped in
  the `k1 == 0` slice.

D. Evidence in code

- `user_map3` tables are built in the `A*A` domain:
  - `src/rune_decrypter_prime/ciphers/generic_map_cipher.py:GenericMapCipher.__init__`
    - `A_key = self.A if ... else self.A * self.A`
    - `k1 = kv // self.A`, `k2 = kv % self.A`
- Keys are mod-reduced by `self.A` before core decrypt:
  - `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:CipherPipelineMixin.decrypt`
    - `key_arr = key_arr % self.A`
- KeyOps hints derive `A` from the cipher/config `A` only:
  - `src/rune_decrypter_prime/core/problem/runtime.py:_gather_keyops_hints`
    - `hints["A"] = int(v)` where `v` comes from `cipher.A`/`cfg.A`
  - `src/rune_decrypter_prime/keyops/registry.py:_alias_kwargs_for_family`
    - `if "A" in out: out["mod"] = out.pop("A")`
- The API also collapses tuple-key specs to length 1:
  - `src/rune_decrypter_prime/api/api_utils.py:resolve_key_length`
    - `if isinstance(key_spec, tuple): return 1`

E. Recommended stress tests

- Domain reachability canary:
  - Define a `user_map3` function where changing `k1` (with fixed `k2`) changes
    the ciphertext/plaintext.
  - Assert that solver-generated keys (or keys after cipher normalization) can
    reach values `>= A` (i.e., encode `k1 > 0`), or fail loudly if not supported.

F. Severity

- solver-blocking (for `user_map3` and affine-like wrappers)

---

## Finding 21 - Beam expansion knobs are split across incompatible parameter contracts

A. Observed behaviour

- The API canonical optimizer keys for Beam use `expand_mode`,
  `top_parents_factor`, and `sample_per_parent`.
- The Beam solver surfaces a different parameter family under `expand.*`
  (e.g., `expand.parent_mode`, `expand.parents_frac`) and writes these to
  telemetry.
- Expansion behaviour is controlled by `_normalize_expand_params()`, which reads
  the API-style keys and ignores the `expand.parent_*` family.
- Parent selection is always top-by-score.

B. Implicit contract

- The parameters users can set at the API boundary must be the same parameters
  that actually control expansion behaviour inside the solver.

C. Risk if violated

- Solver-degrading and tuning-hostile: documented/tuned knobs can be rejected at
  the API boundary or accepted but ignored in the solver.
- On hard problems this creates "tuning folklore" where changes appear to do
  nothing for reasons unrelated to the user's intent.

D. Evidence in code

- API canonical keys do not include the `expand.parent_*` family:
  - `src/rune_decrypter_prime/api/_resolve.py:_CANON_OPTS["beam"]`
    - includes `expand_mode`, `sample_per_parent`, `top_parents_factor`
- Solver reads and reports `expand.parent_*` knobs:
  - `src/rune_decrypter_prime/solvers/beam.py:BeamSolver.solve`
    - `p_mode = get_param("expand.parent_mode", ...)`
    - `parents_frac = get_param("expand.parents_frac", ...)`
- Solver behaviour is controlled by a different key family:
  - `src/rune_decrypter_prime/solvers/beam.py:BeamSolver._normalize_expand_params`
    - reads `expand_mode`, `top_parents_factor`, `sample_per_parent`
- Parent selection is always deterministic top-k:
  - `src/rune_decrypter_prime/solvers/beam.py:BeamSolver._expand_round_safe`
    - `parent_idx = np.argsort(scores)[-parents:][::-1]`

E. Recommended stress tests

- Knob-effect canary (fixed seed, 1 round):
  1) Attempt to pass `expand.parents_frac` via the public API and assert whether
     it is accepted or rejected (both outcomes should be explicit).
  2) Vary `expand.parent_mode` between "top" and "stochastic" and assert parent
     identities change; if they do not, the knob is disconnected.

F. Severity

- solver-degrading

---

## Additional open questions from this pass

6) LM smoothing isolation policy:
   - Should `_load_bin` cache be keyed by (path, smoothing, oov_policy, alpha),
     or should it return immutable buffers that the native layer copies?
7) `user_map3` key representation:
   - Is the canonical representation a single encoded key-value in `0..A*A-1`,
     or two explicit key streams? The current API surfaces both ideas.
8) Beam parameter contract:
   - Which parameter family is the source of truth (`expand_mode` vs `expand.*`)?
