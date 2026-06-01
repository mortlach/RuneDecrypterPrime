# RDP Audit Reparse - Active Stage TODO (auto-extracted)

This file is auto-generated from the audit sources in planning/audit1.

## Status note (2026-02-03)
Chunks 0 through 7 are marked Complete in planning/audit1/VERIFICATION_TRACKER.md.
Use that tracker as the source of truth for current status and evidence.

## Sources read
- AUDIT_INDEX.md
- RDP_Audit_Source_Reference_Map_v2.md
- bug_hunt_linenum.txt
- bug_hunt.txt
- RuneDecrypterPrime Codebase Forensic Audit.pdf
- RDP_Audit_pdf_linenum.txt (generated locally for line references)

## Active stage TODO (concrete, ordered)
- [ ] Create or update a decisions log (suggested: `docs/decisions/audit1.md`) and answer all PDF-Q items before any refactor. Record the final contract and rationale, then link each decision back to its ID.
- [ ] Triage every item below (PDF-* and BH-*): verify the behavior in current code, add file+line evidence, and mark status as Verified / Not Reproduced / Needs Clarification.
- [ ] WLI contract alignment (verified mismatch exists): after deciding the canonical format, update all WLI producers and consumers to the same contract and add validation at the API-core boundary.
- [ ] WLI missing-data handling (verified behavior exists): decide whether to error or disable WLI models when `use_word_breaks=True` but WLI is absent; add a guard test.
- [ ] Add the full proposed test suite (PDF-T* and BH-B* lists) and mark each new test with a pytest marker (`tier_a` for fast contracts).
- [ ] Build a minimal regression harness: run targeted pytest subsets for scoring, API, ciphers, and solver determinism after each change.

## Verified in current code (cross-checks already done)
- WLI contract mismatch across layers:
  - API normalizer asserts WLI as `[start, length]` and `wli_from_text` emits `[start, length]` with absolute start. See `src/rune_decrypter_prime/api/normalize.py:256` and `src/rune_decrypter_prime/api/normalize.py:264`.
  - CipherConfig validates WLI as `(start, end)` pairs. See `src/rune_decrypter_prime/core/config/cipher.py:71`.
  - LMPrime validator expects WLI as `(pos_in_word, len)` with `0 <= pos < len <= 63`. See `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:396`.
  - Torch scorer masks WLI pos/len to 6 bits (`0x3F`). See `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:424`.
- Span conversion in API pipeline exists (can distort multi-word WLI depending on chosen contract): `src/rune_decrypter_prime/api/pipeline_helpers.py:234`.
- WLI models can be active even when WLI data is missing (weights are normalized regardless): `src/rune_decrypter_prime/scoring/rune_scorer.py:1073`, `src/rune_decrypter_prime/scoring/rune_scorer.py:1085`.
- `maximize` appears in config, but is not referenced in solver logic (objective-direction behavior needs explicit verification). `rg -n \"maximize\" src/rune_decrypter_prime` shows only config/data hits.

## Tests, checks, docs, decisions (comprehensive suite)
### Tests to implement (from PDF + bug_hunt)
- PDF-T01 `tests/api/test_wli_invariants.py` (test_wli_invariants)
- PDF-T02 `tests/api/test_wli_parity.py` (test_wli_parity)
- PDF-T03 `tests/core/test_permutation_wli.py` (test_permutation_wli)
- PDF-T04 `tests/solver/test_objective_direction.py` (test_objective_direction)
- PDF-T05 Score Precision Near-Tie (define file and test name)
- PDF-T06 `tests/scoring/test_wli_missing.py` (test_wli_missing)
- PDF-T07 `tests/solver/test_determinism.py` (test_determinism)
- PDF-T08 `tests/solver/test_seed_validation.py` (test_seed_validation)
- PDF-T09 `tests/core/test_interruptor_permutation.py` (test_interruptor_permutation)
- PDF-T10 `tests/core/test_variable_interruptors.py` (test_variable_interruptors)
- PDF-T11 Telemetry Permutation Reporting (define file + test name)
- PDF-T12 `tests/api/test_encoding_direction.py` (test_encoding_direction)
- PDF-T13 `tests/scoring/test_lm_smoothing.py` (test_lm_smoothing)
- PDF-T14 `tests/ciphers/test_user_map3_domain.py` (test_user_map3_domain)
- BH-B01: test_wli_string_path_contract_poslen, test_wli_config_contract_is_consistent_with_hamming, test_wli_uint8_overflow_guard
- BH-B02: test_interruptor_remove_insert_roundtrip, test_interruptor_remove_then_text_permutation_then_inverse_roundtrip, test_wli_alignment_under_text_permutation
- BH-B03: test_composed_cipher_with_interruptors_roundtrip, test_periodic_columnar_roundtrip_lengths_not_multiple_of_columns, test_periodic_substitution_encrypt_decrypt_roundtrip_random
- BH-B04: test_batch_vs_scalar_ordering_near_ties, test_ecdf_dtype_knob_is_real, test_numpy_vs_torch_ranking_parity_fixed_candidates

### Checks to run (after each change)
- `py -3 -m pytest -m tier_a`
- `py -3 -m pytest tests/scoring tests/api tests/core tests/ciphers`
- `py -3 -m pytest -m guardrails`
- `py -3 -m pytest -m smoke`
- CUDA-specific: `py -3 -m pytest -m cuda` (only on CUDA hosts)

### Docs to update after decisions
- WLI contract and usage: `docs/guides/scoring.md`, `docs/reference/api/normalize.md`, `docs/reference/api/pipeline_helpers.md`, `docs/reference/scoring/rune_scorer.md`, `docs/architecture/data.md`, `docs/guides/api_deep.md`
- Objective direction semantics: `docs/guides/scoring.md`, `docs/reference/core/config/scoring.md`
- Interruptor/permutation contract: `docs/guides/architecture.md`, `docs/reference/api/pipeline.md`
- user_map3 key representation: `docs/README.md` or a dedicated cipher guide if one exists

### Decisions to record (PDF-Q list)
- PDF-Q01 Canonical WLI Format
- PDF-Q02 Span vs Pos Usage
- PDF-Q03 Permutation semantics with interruptors
- PDF-Q04 Objective direction handling
- PDF-Q05 Score dtype policy
- PDF-Q06 Language model cache isolation
- PDF-Q07 user_map3 key representation
- PDF-Q08 Beam parameters source of truth

## Exact prompt (use this to execute the plan with a fresh agent)
You are working in the local repo `C:\\Users\\sjduk\\OneDrive\\Documents\\github\\RuneDecrypterPrime`.
Read `planning/audit1/AUDIT_INDEX.md`, `planning/audit1/RDP_Audit_Source_Reference_Map_v2.md`,
`planning/audit1/bug_hunt_linenum.txt`, and `planning/audit1/RDP_Audit_pdf_linenum.txt`.
Do not assume any audit finding is still valid. For each item (PDF-* and BH-*), verify behavior in the current code,
cite file paths and line numbers, and mark status in `planning/audit1/ACTIVE_STAGE_TODO.md`.
Answer the PDF-Q decisions first, then align contracts (especially WLI), then implement the proposed tests (PDF-T* and BH-B*),
mark tests with pytest markers, update docs listed above, and run the checks in the same file.
If any evidence cannot be verified, explicitly say what file or context is missing and ask for guidance.
Do not make changes without linking them to a specific audit item ID.

## Open questions (need user input)
- Should I treat "active stage" as decisions + verification only, or include remediation fixes in this pass?
- Where do you want the decision log stored (`docs/decisions/audit1.md` ok, or another location)?
- For missing proposed tests, should I create new files even if they are not referenced elsewhere, or consolidate into existing test modules?
- Which pytest marker should be used for new contract tests (`tier_a` by default)?

## Open design decisions (PDF-Q)
| ID | Title | Source Ref | Evidence Files (audit -> repo) | Tests Mentioned |
| --- | --- | --- | --- | --- |
| PDF-Q01 | Canonical WLI Format | PDF p15 l32-l35 |  |  |
| PDF-Q02 | Span vs Pos Usage | PDF p15 l36 – p16 l2 |  |  |
| PDF-Q03 | Permutation semantics with interruptors | PDF p16 l3-l7 |  |  |
| PDF-Q04 | Objective direction handling | PDF p16 l8-l11 |  |  |
| PDF-Q05 | Score dtype policy | PDF p16 l12-l16 |  |  |
| PDF-Q06 | Language model cache isolation | PDF p16 l17-l20 |  |  |
| PDF-Q07 | user_map3 key representation | PDF p16 l21-l25 |  |  |
| PDF-Q08 | Beam parameters source of truth | PDF p16 l26-l28 |  |  |

## PDF findings (PDF-xx)
| ID | Title | Source Ref | Evidence Files (audit -> repo) | Tests Mentioned |
| --- | --- | --- | --- | --- |
| PDF-01 | Objective Direction Misalignment (NEGLOGP vs Maximize | PDF p01 l13-l40 |  |  |
| PDF-02 | Floating-Point Precision | PDF p02 l1-l24 |  |  |
| PDF-03 | WLI Model Activation Without WLI Data (Missing-Data Handling | PDF p02 l25 – p03 l13 |  |  |
| PDF-04 | Language Model Smoothing Cache Contamination | PDF p03 l14 – p04 l3 |  |  |
| PDF-05 | Inconsistent Determinism Defaults | PDF p04 l4-l20 |  |  |
| PDF-06 | Silent Seed Key Replacement on Normalization Failure | PDF p04 l21 – p05 l6 |  |  |
| PDF-07 | Beam Expansion Parameter Mismatch (API vs Solver Implementation | PDF p05 l7-l51 | solvers/beam.py -> src/rune_decrypter_prime/solvers/beam.py |  |
| PDF-08 | Composite Key Length and Variable-Interruptor Handling | PDF p06 l1 – p07 l17 |  |  |
| PDF-09 | WLI Semantic Mismatch (Start/End vs Pos/Len | PDF p07 l18 – p08 l14 |  |  |
| PDF-10 | WLI Span Conversion Glitch on Multi-Word Input | PDF p08 l15 – p09 l12 |  |  |
| PDF-11 | Permutation Length Reported in Wrong Terms | PDF p09 l13-l41 | telemetry/pipeline.py -> src/rune_decrypter_prime/telemetry/pipeline.py |  |
| PDF-12 | English Plaintext Input Ignores Specified Encoding Direction | PDF p10 l1 – p11 l6 |  |  |
| PDF-13 | Collapsed Key Space for user_map3 (Affine Cipher | PDF p11 l7-l50 | core/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py, legacy/rune_decrypter_prime/core/problem/runtime.py... |  |

## PDF proposed tests (PDF-Txx)
| ID | Title | Source Ref | Evidence Files (audit -> repo) | Tests Mentioned |
| --- | --- | --- | --- | --- |
| PDF-T01 | WLI Invariant Canary | PDF p13 l10-l16 | tests/api/test_wli_invariants.py (not found) | test_wli_invariants |
| PDF-T02 | WLI vs Runeglish Parity | PDF p13 l17-l22 | tests/api/test_wli_parity.py (not found) | test_wli_parity |
| PDF-T03 | WLI Permutation Alignment | PDF p13 l23-l28 | tests/core/test_permutation_wli.py (not found) | test_permutation_wli |
| PDF-T04 | Objective Direction Canary | PDF p13 l29-l34 | tests/solver/test_objective_direction.py (not found) | test_objective_direction |
| PDF-T05 | Score Precision Near-Tie | PDF p13 l35 – p14 l3 |  |  |
| PDF-T06 | WLI Missing-Data Guard | PDF p14 l4-l11 | tests/scoring/test_wli_missing.py (not found) | test_wli_missing |
| PDF-T07 | Legacy vs Main Determinism | PDF p14 l12-l17 | tests/solver/test_determinism.py (not found) | test_determinism |
| PDF-T08 | Seed Replacement Detection | PDF p14 l18-l24 | tests/solver/test_seed_validation.py (not found) | test_seed_validation |
| PDF-T09 | test_interruptor_permutation.py | PDF p14 l25-l31 |  | test_interruptor_permutation |
| PDF-T10 | Variable Interruptor Count Guard | PDF p14 l32-l37 | tests/core/test_variable_interruptors.py (not found) | test_variable_interruptors |
| PDF-T11 | Telemetry Permutation Reporting | PDF p14 l38 – p15 l2 |  |  |
| PDF-T12 | Encoding Direction Consistency | PDF p15 l3-l10 | tests/api/test_encoding_direction.py (not found) | test_encoding_direction |
| PDF-T13 | LM Cache Isolation | PDF p15 l11-l17 | tests/scoring/test_lm_smoothing.py (not found) | test_lm_smoothing |
| PDF-T14 | User Map3 Full-Domain Test | PDF p15 l18-l45 | tests/ciphers/test_user_map3_domain.py (not found) | test_user_map3_domain |

## bug_hunt blocks (BH-Bxx)
| ID | Title | Source Ref | Evidence Files (audit -> repo) | Tests Mentioned |
| --- | --- | --- | --- | --- |
| BH-B01 | WLI is two different things (and it leaks across boundaries | BH L1669-L1728 | api/normalize.py -> src/rune_decrypter_prime/api/normalize.py; core/config/cipher.py -> src/rune_decrypter_prime/core/config/cipher.py; scoring/hamming/Hamming.h -> src/rune_decrypter_prime/scoring/hamming/Hamming.h; scoring/rune_scorer.py -> src/rune_decrypter_prime/scoring/rune_scorer.py | test_wli_config_contract_is_consistent_with_hamming, test_wli_string_path_contract_poslen, test_wli_uint8_overflow_guard |
| BH-B02 | Interruptors + text permutation: alignment traps | BH L1729-L1785 | ciphers/ciphers_pipeline.py -> src/rune_decrypter_prime/ciphers/ciphers_pipeline.py; utils/interrupter.py -> src/rune_decrypter_prime/utils/interrupter.py | test_interruptor_remove_insert_roundtrip, test_interruptor_remove_then_text_permutation_then_inverse_roundtrip, test_wli_alignment_under_text_permutation |
| BH-B03 | Periodic substitution + columnar + interruptors: round-trip invariants | BH L1786-L1825 | ciphers/periodic_columnar_cipher.py -> src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py; ciphers/periodic_substitution_cipher.py -> src/rune_decrypter_prime/ciphers/periodic_substitution_cipher.py | test_composed_cipher_with_interruptors_roundtrip, test_periodic_columnar_roundtrip_lengths_not_multiple_of_columns, test_periodic_substitution_encrypt_decrypt_roundtrip_random |
| BH-B04 | Scoring integrity (dtype honesty, batch/scalar honesty | BH L1826-L2296 | api/normalize.py -> src/rune_decrypter_prime/api/normalize.py; ciphers/ciphers_pipeline.py -> src/rune_decrypter_prime/ciphers/ciphers_pipeline.py | test_batch_vs_scalar_ordering_near_ties, test_ecdf_dtype_knob_is_real, test_numpy_vs_torch_ranking_parity_fixed_candidates |

## bug_hunt items (BH-*)
| ID | Title | Source Ref | Evidence Files (audit -> repo) | Tests Mentioned |
| --- | --- | --- | --- | --- |
| BH-10A | Engine seed propagation (good, but note what it guarantees | BH L4953-L4980 | rune_decrypter_prime/core/engine/engine.py -> src/rune_decrypter_prime/core/engine/engine.py, legacy/rune_decrypter_prime/core/engine/engine.py... |  |
| BH-10B | Legacy build_optimizer() uses entropy RNG (high-risk footgun | BH L4981-L5005 | rune_decrypter_prime/core/solver_engine.py -> src/rune_decrypter_prime/core/solver_engine.py, legacy/rune_decrypter_prime/core/solver_engine.py... |  |
| BH-10C | Hybrid phase RNG derivation depends on internal RNG state shape (brittle | BH L5006-L5040 | rune_decrypter_prime/solvers/hybrid.py -> src/rune_decrypter_prime/solvers/hybrid.py, legacy/rune_decrypter_prime/new_solver/hybrid.py... |  |
| BH-10D | Entropy RNG fallback in SolverBase seed normalisation (should not exist in a strict-deterministic framework | BH L5041-L5070 | rune_decrypter_prime/solvers/solver_base.py -> src/rune_decrypter_prime/solvers/solver_base.py, legacy/rune_decrypter_prime/new_solver/solver_base.py... |  |
| BH-10E | Torch determinism knobs are set globally (good intent, but device parity still needs explicit tests | BH L5071-L5285 | rune_decrypter_prime/scoring/torch_rune_scorer.py -> src/rune_decrypter_prime/scoring/torch_rune_scorer.py, legacy/rune_decrypter_prime/scoring/torch_rune_scorer.py... |  |
| BH-8A | Seed normalisation and “default determinism | BH L4344-L4385 | Copy/api/pipeline.py -> src/rune_decrypter_prime/api/pipeline.py, src/rune_decrypter_prime/telemetry/pipeline.py...; Copy/core/config/run.py -> src/rune_decrypter_prime/api/run.py, src/rune_decrypter_prime/core/config/run.py...; Copy/core/engine/engine.py -> src/rune_decrypter_prime/core/engine/engine.py, legacy/rune_decrypter_prime/core/engine/engine.py... |  |
| BH-8B | initial_text_permutation_indices normalisation exists but is not used | BH L4386-L4429 | Copy/api/normalize.py -> src/rune_decrypter_prime/api/normalize.py, legacy/rune_decrypter_prime/api/normalize.py...; Copy/core/problem/instance.py -> src/rune_decrypter_prime/core/problem/instance.py, legacy/rune_decrypter_prime/core/problem/instance.py... |  |
| BH-8C | Ciphertext index coercion can silently wrap invalid values | BH L4430-L4468 | Copy/api/normalize.py -> src/rune_decrypter_prime/api/normalize.py, legacy/rune_decrypter_prime/api/normalize.py...; Copy/core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py, legacy/rune_decrypter_prime/core/problem/runtime.py... |  |
| BH-8D | Scorer param normalisation has keys that the “strict” validator will reject | BH L4469-L4513 | Copy/api/_resolve.py -> src/rune_decrypter_prime/api/_resolve.py, legacy/rune_decrypter_prime/api/_resolve.py...; Copy/api/normalize.py -> src/rune_decrypter_prime/api/normalize.py, legacy/rune_decrypter_prime/api/normalize.py... |  |
| BH-8E | Legacy win” is silently swallowed / conditionally merged into objective | BH L4514-L4548 | Copy/api/normalize.py -> src/rune_decrypter_prime/api/normalize.py, legacy/rune_decrypter_prime/api/normalize.py... |  |
| BH-8F | WLI is structurally “always there” in core configs, and scoring defaults heavily weight it | BH L4549-L4608 | Copy/api/normalize.py -> src/rune_decrypter_prime/api/normalize.py, legacy/rune_decrypter_prime/api/normalize.py...; Copy/core/config/scoring.py -> src/rune_decrypter_prime/core/config/scoring.py, legacy/rune_decrypter_prime/core/config/scoring.py... |  |
| BH-8G | Interruptor config precedence can silently override user intent | BH L4609-L4696 | Copy/core/config/cipher.py -> src/rune_decrypter_prime/core/config/cipher.py, legacy/rune_decrypter_prime/core/config/cipher.py... |  |
| BH-F2.1 | Window span maths is centralised and mostly consistent (good), but relies on a “length means X” contract | BH L2561-L2600 | rune_decrypter_prime/scoring/windowing.py -> src/rune_decrypter_prime/scoring/windowing.py |  |
| BH-F2.2 | NumPy backend implements WISE by injecting tags per window, and NOSE forbids boundary tags | BH L2601-L2644 | rune_decrypter_prime/scoring/rune_scorer.py -> src/rune_decrypter_prime/scoring/rune_scorer.py, legacy/rune_decrypter_prime/scoring/rune_scorer.py... |  |
| BH-F2.3 | Torch backend does not support WISE at all, and its token handling differs | BH L2645-L2693 | rune_decrypter_prime/scoring/torch_rune_scorer.py -> src/rune_decrypter_prime/scoring/torch_rune_scorer.py, legacy/rune_decrypter_prime/scoring/torch_rune_scorer.py... |  |
| BH-F2.4 | Short-text (“no windows”) behaviour differs between NumPy and Torch when Hamming/WLI is enabled | BH L2694-L2745 | rune_decrypter_prime/scoring/rune_scorer.py -> src/rune_decrypter_prime/scoring/rune_scorer.py, legacy/rune_decrypter_prime/scoring/rune_scorer.py...; rune_decrypter_prime/scoring/torch_rune_scorer.py -> src/rune_decrypter_prime/scoring/torch_rune_scorer.py, legacy/rune_decrypter_prime/scoring/torch_rune_scorer.py... |  |
| BH-F2.5 | WISE “interior mean” naming/semantics look inconsistent (even before we discuss enabling WISE | BH L2746-L2842 | rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py -> src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py, legacy/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py...; rune_decrypter_prime/scoring/rune_scorer.py -> src/rune_decrypter_prime/scoring/rune_scorer.py, legacy/rune_decrypter_prime/scoring/rune_scorer.py... |  |
| BH-F3.1 | Global LM table cache is writable and is expected to be mutated in-place (run-order hazard | BH L2855-L2898 | scoring/language_model/language_model_prime.py -> src/rune_decrypter_prime/scoring/language_model/language_model_prime.py |  |
| BH-F3.2 | Runtime cache keys include smoothing, but the underlying global bin cache does not (isolation is leaky | BH L2899-L2933 | scoring/language_model/language_model_prime.py -> src/rune_decrypter_prime/scoring/language_model/language_model_prime.py; scoring/language_model/language_model_prime_runtime.py -> src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py |  |
| BH-F3.3 | ECDF cache selection ignores window size (win), despite Bucket/meta carrying it (hidden assumption: W fixed | BH L2934-L2988 | scoring/language_model/language_model_prime_runtime.py -> src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py |  |
| BH-F3.4 | Cached arrays are returned by reference (accidental mutation can corrupt later results | BH L2989-L3020 |  |  |
| BH-F3.5 | ECDF float32 “working buffers” selection is not fully validated (q32 can lose strict increase | BH L3021-L3095 |  |  |
| BH-S01 | Interruptor symbols are always fixed from the ciphertext (and interrupt_sym is effectively unused | BH L2307-L2354 | rune_decrypter_prime/ciphers/ciphers_pipeline.py -> src/rune_decrypter_prime/ciphers/ciphers_pipeline.py, src/output/share/2025-11-17T08-15-02-0800__share__rune-decrypter/src_20251117_081511_share/repo/rune_decrypter_prime/ciphers/ciphers_pipeline.py; rune_decrypter_prime/core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py, legacy/rune_decrypter_prime/core/problem/runtime.py...; rune_decrypter_prime/utils/interrupter.py -> src/rune_decrypter_prime/utils/interrupter.py, legacy/rune_decrypter_prime/utils/interrupter.py... |  |
| BH-S02 | Pool-mode interruptor search forces CompositeKeyOps (key contains interrupt positions), but scoring/WLI metadata stays global and static | BH L2355-L2417 | rune_decrypter_prime/core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py, legacy/rune_decrypter_prime/core/problem/runtime.py... |  |
| BH-S03 | initial_text_permutation_indices is applied after interruptor removal and requires fixed core text length — variable interruptor count will crash | BH L2418-L2471 | rune_decrypter_prime/ciphers/ciphers_pipeline.py -> src/rune_decrypter_prime/ciphers/ciphers_pipeline.py, src/output/share/2025-11-17T08-15-02-0800__share__rune-decrypter/src_20251117_081511_share/repo/rune_decrypter_prime/ciphers/ciphers_pipeline.py; rune_decrypter_prime/keyops/composite.py -> src/rune_decrypter_prime/keyops/composite.py; rune_decrypter_prime/utils/transposition.py -> src/rune_decrypter_prime/utils/transposition.py, legacy/rune_decrypter_prime/utils/transposition.py... |  |
| BH-S04 | InterruptorConfig exists, but key parts of it are not actually enforced/used (danger: “config looks supported” but behaviour is different | BH L2472-L2560 | rune_decrypter_prime/core/config/interruptor.py -> src/rune_decrypter_prime/core/config/interruptor.py; rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py -> src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py, legacy/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py...; rune_decrypter_prime/scoring/rune_scorer.py -> src/rune_decrypter_prime/scoring/rune_scorer.py, legacy/rune_decrypter_prime/scoring/rune_scorer.py...; rune_decrypter_prime/scoring/torch_rune_scorer.py -> src/rune_decrypter_prime/scoring/torch_rune_scorer.py, legacy/rune_decrypter_prime/scoring/torch_rune_scorer.py...; rune_decrypter_prime/scoring/windowing.py -> src/rune_decrypter_prime/scoring/windowing.py |  |
| BH-S05 | device” semantics are inconsistent across core vs backend selection | BH L3099-L3142 | backends/xp.py -> src/rune_decrypter_prime/backends/xp.py; core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py; core/types.py -> src/rune_decrypter_prime/core/types.py |  |
| BH-S06 | core runtime can materialise ciphertext as CUDA arrays even though ciphers are NumPy-only | BH L3143-L3177 | ciphers/ciphers_pipeline.py -> src/rune_decrypter_prime/ciphers/ciphers_pipeline.py; core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py |  |
| BH-S07 | Score dtype “float64” is mostly a wrapper; ordering is still determined by float32 scorers | BH L3178-L3213 | core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py; scoring/rune_scorer.py -> src/rune_decrypter_prime/scoring/rune_scorer.py; scoring/unified_rune_scorer.py -> src/rune_decrypter_prime/scoring/unified_rune_scorer.py |  |
| BH-S08 | UnifiedRuneScorer ignores the ScoringConfig.dtype intent and hard-codes float32 semantics | BH L3214-L3246 | scoring/unified_rune_scorer.py -> src/rune_decrypter_prime/scoring/unified_rune_scorer.py |  |
| BH-S09 | Key dtype story is inconsistent (docs say uint8; core uses int16; ciphers sometimes enforce uint8 | BH L3247-L3347 | audit_pack_extract/src/rune_decrypter_prime/solvers/beam.py -> src/rune_decrypter_prime/solvers/beam.py, legacy/rune_decrypter_prime/new_solver/beam.py...; audit_pack_extract/src/rune_decrypter_prime/solvers/ga.py -> src/rune_decrypter_prime/solvers/ga.py, legacy/rune_decrypter_prime/new_solver/ga.py...; audit_pack_extract/src/rune_decrypter_prime/solvers/hybrid.py -> src/rune_decrypter_prime/solvers/hybrid.py, legacy/rune_decrypter_prime/new_solver/hybrid.py...; audit_pack_extract/src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py -> src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py; audit_pack_extract/src/rune_decrypter_prime/solvers/sa.py -> src/rune_decrypter_prime/solvers/sa.py, legacy/rune_decrypter_prime/new_solver/sa.py...; audit_pack_extract/src/rune_decrypter_prime/solvers/solver_base.py -> src/rune_decrypter_prime/solvers/solver_base.py, legacy/rune_decrypter_prime/new_solver/solver_base.py...; ciphers/columnar_transposition_cipher.py -> src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py; keyops/permutation_ops.py -> src/rune_decrypter_prime/keyops/permutation_ops.py |  |
| BH-S10 | SolverBase early-stop state has two competing implementations + doc drift | BH L3350-L3399 | src/rune_decrypter_prime/solvers/solver_base.py -> src/rune_decrypter_prime/solvers/solver_base.py |  |
| BH-S11 | Improvement threshold documentation says “≥” but code uses strict | BH L3400-L3430 |  |  |
| BH-S12 | Tie-handling in top-K selection is not stable; ties can create cross-run drift | BH L3431-L3475 | src/rune_decrypter_prime/solvers/beam.py -> src/rune_decrypter_prime/solvers/beam.py; src/rune_decrypter_prime/solvers/ga.py -> src/rune_decrypter_prime/solvers/ga.py |  |
| BH-S13 | SA acceptance and “best update” are consistent, but there is an unused knob | BH L3476-L3512 | src/rune_decrypter_prime/solvers/sa.py -> src/rune_decrypter_prime/solvers/sa.py |  |
| BH-S14 | Kaeding plateau logic can override plateau based on pct improvements, but telemetry state can become inconsistent | BH L3513-L3594 | src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py -> src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py; src/rune_decrypter_prime/solvers/solver_base.py -> src/rune_decrypter_prime/solvers/solver_base.py |  |
| BH-S15 | KeyOps verb registry + capability truthfulness (base class | BH L3599-L3636 | Copy/keyops/base_keyops.py -> src/rune_decrypter_prime/keyops/base_keyops.py, legacy/rune_decrypter_prime/keyops/base_keyops.py... |  |
| BH-S16 | RNG API consistency (Generator vs RandomState) inside KeyOps | BH L3637-L3662 | Copy/io/rng.py -> src/rune_decrypter_prime/io/rng.py, legacy/rune_decrypter_prime/io/rng.py...; Copy/keyops/base_keyops.py -> src/rune_decrypter_prime/keyops/base_keyops.py, legacy/rune_decrypter_prime/keyops/base_keyops.py... |  |
| BH-S17 | GA recombination path can crash for KeyOps that don’t override recombine | BH L3663-L3693 | Copy/solvers/ga.py -> src/rune_decrypter_prime/solvers/ga.py, legacy/rune_decrypter_prime/new_solver/ga.py... |  |
| BH-S18 | CompositeKeyOps interruptor mutation locality (repair steps can amplify a “small” move | BH L3694-L3746 | Copy/keyops/composite.py -> src/rune_decrypter_prime/keyops/composite.py |  |
| BH-S19 | Repair to permutation” normalisation can conceal upstream key corruption | BH L3747-L3834 | Copy/keyops/permutation_ops.py -> src/rune_decrypter_prime/keyops/permutation_ops.py, legacy/rune_decrypter_prime/keyops/permutation_ops.py... |  |
| BH-S20 | Periodic substitution key validity is assumed (not enforced) — encryption can silently go wrong | BH L3835-L3883 | rune_decrypter_prime/ciphers/periodic_substitution_cipher.py -> src/rune_decrypter_prime/ciphers/periodic_substitution_cipher.py |  |
| BH-S21 | Columnar transposition core logic looks internally consistent for edge lengths (but batch semantics are “broadcast plaintext | BH L3884-L3936 | rune_decrypter_prime/ciphers/columnar_transposition_cipher.py -> src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py, legacy/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py... |  |
| BH-S22 | Pipeline “mod_keys” can hide invalid substitution keys by wrapping (worth deciding explicitly | BH L3937-L4008 | rune_decrypter_prime/ciphers/ciphers_pipeline.py -> src/rune_decrypter_prime/ciphers/ciphers_pipeline.py, src/output/share/2025-11-17T08-15-02-0800__share__rune-decrypter/src_20251117_081511_share/repo/rune_decrypter_prime/ciphers/ciphers_pipeline.py; rune_decrypter_prime/ciphers/columnar_transposition_cipher.py -> src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py, legacy/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py...; rune_decrypter_prime/ciphers/periodic_columnar_cipher.py -> src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py; rune_decrypter_prime/ciphers/periodic_substitution_cipher.py -> src/rune_decrypter_prime/ciphers/periodic_substitution_cipher.py |  |
| BH-S23 | Cipher pipeline composition (interruptors + text transposition/permutation + core cipher | BH L4010-L4072 | rune_decrypter_prime/ciphers/ciphers_pipeline.py -> src/rune_decrypter_prime/ciphers/ciphers_pipeline.py, src/output/share/2025-11-17T08-15-02-0800__share__rune-decrypter/src_20251117_081511_share/repo/rune_decrypter_prime/ciphers/ciphers_pipeline.py |  |
| BH-S24 | TranspositionManager “perm” mode (invertibility + determinism | BH L4073-L4128 | rune_decrypter_prime/utils/transposition.py -> src/rune_decrypter_prime/utils/transposition.py, legacy/rune_decrypter_prime/utils/transposition.py... |  |
| BH-S25 | PeriodicColumnarCipher core correctness (periodic substitution + columnar transposition | BH L4129-L4216 | rune_decrypter_prime/ciphers/periodic_columnar_cipher.py -> src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py |  |
| BH-S26 | Columnar transposition remainder handling (edge lengths | BH L4217-L4257 | rune_decrypter_prime/ciphers/columnar_transposition_cipher.py -> src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py, legacy/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py... |  |
| BH-S27 | Interruptors + initial_text_permutation_indices interaction (length coupling | BH L4258-L4341 | rune_decrypter_prime/core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py, legacy/rune_decrypter_prime/core/problem/runtime.py...; utils/transposition.py -> src/rune_decrypter_prime/utils/transposition.py |  |
| BH-S28 | initial_text_permutation_indices normalisation / validation | BH L4697-L4739 | api/normalize.py -> src/rune_decrypter_prime/api/normalize.py; core/problem/instance.py -> src/rune_decrypter_prime/core/problem/instance.py |  |
| BH-S29 | Solver span duration is computed from mixed clocks | BH L4740-L4780 | solvers/solver_base.py -> src/rune_decrypter_prime/solvers/solver_base.py; telemetry/events.py -> src/rune_decrypter_prime/telemetry/events.py |  |
| BH-S30 | eval_keys” / “eval_batches” counters exist but are never updated | BH L4781-L4812 | core/problem/runtime.py -> src/rune_decrypter_prime/core/problem/runtime.py |  |
| BH-S31 | Run envelope fields use setdefault and can go stale if a problem is reused | BH L4813-L4847 | telemetry/events.py -> src/rune_decrypter_prime/telemetry/events.py |  |
| BH-S32 | Telemetry attachment uses setdefault and claims “shallow copy” but still shares references | BH L4848-L4879 | telemetry/events.py -> src/rune_decrypter_prime/telemetry/events.py |  |
| BH-S33 | Engine records scorer impl/dtype via optional methods, so telemetry can be “unknown” even when known | BH L4880-L4950 | core/engine/engine.py -> src/rune_decrypter_prime/core/engine/engine.py |  |
