# Merge Integration Plan: Local `experimentalBigBadAssetMove` + Network `experimental/nowli-path-clean`

Date: 2026-03-08  
Local repo/branch: `experimentalBigBadAssetMove` @ `bf092797ffdf328ea3d42fbaeecdf0f0701c3d80`  
Network repo/branch: `experimental/nowli-path-clean` @ `e71600c5275bc2c640244d8cfd8b7d8a925f807c`

## 0) Preconditions and constraints

- `AGENTS.md` checked and applied.
- `repo_links.csv` is not present in either compared tree, so this plan is based on direct Git tree comparison (not inventory-audited).
- Merge objective is first-class integration: keep local platform architecture and land network scoring capability.
- This is a planned port, not a blind merge.
- Review comments from 2026-03-08 are incorporated below as locked decisions for slice 1.

## 1) Comparison snapshot (blob-level, HEAD-to-HEAD)

### `src/rune_decrypter_prime/api`
- only_local: 0
- only_network: 0
- changed_common: 3
- changed:  
  - `src/rune_decrypter_prime/api/__init__.py`  
  - `src/rune_decrypter_prime/api/_resolve.py`  
  - `src/rune_decrypter_prime/api/data_helpers.py`

### `src/rune_decrypter_prime/core`
- only_local: 0
- only_network: 1
- changed_common: 3
- only_network:  
  - `src/rune_decrypter_prime/core/hamming_dictionary_policy.py`
- changed:  
  - `src/rune_decrypter_prime/core/config/run.py`  
  - `src/rune_decrypter_prime/core/config/scoring.py`  
  - `src/rune_decrypter_prime/core/problem/runtime.py`

### `src/rune_decrypter_prime/scoring`
- only_local: 7
- only_network: 8
- changed_common: 9
- local-only:  
  - `src/rune_decrypter_prime/scoring/objective_normalize.py`  
  - `src/rune_decrypter_prime/scoring/scorer_report.py`  
  - `src/rune_decrypter_prime/scoring/scorer_report_builder.py`  
  - `src/rune_decrypter_prime/scoring/torch_backend/__init__.py`  
  - `src/rune_decrypter_prime/scoring/torch_backend/hash.py`  
  - `src/rune_decrypter_prime/scoring/torch_backend/packing.py`  
  - `src/rune_decrypter_prime/scoring/torch_backend/probe.py`
- network-only:  
  - `src/rune_decrypter_prime/scoring/hamming/dictionary_assets.py`  
  - `src/rune_decrypter_prime/scoring/span_hamming/ecdf_interp.py`  
  - `src/rune_decrypter_prime/scoring/span_hamming/lm_assets_v2.py`  
  - `src/rune_decrypter_prime/scoring/word_ngrams/__init__.py`  
  - `src/rune_decrypter_prime/scoring/word_ngrams/in_memory.py`  
  - `src/rune_decrypter_prime/scoring/word_ngrams/runtime.py`  
  - `src/rune_decrypter_prime/scoring/word_ngrams/scorer.py`  
  - `src/rune_decrypter_prime/scoring/word_ngrams/sqlite_model.py`
- changed:  
  - `src/rune_decrypter_prime/scoring/base_scorer.py`  
  - `src/rune_decrypter_prime/scoring/hamming/loader.py`  
  - `src/rune_decrypter_prime/scoring/language_model/paths.py`  
  - `src/rune_decrypter_prime/scoring/readme.txt`  
  - `src/rune_decrypter_prime/scoring/rune_scorer.py`  
  - `src/rune_decrypter_prime/scoring/scoring_adapter.py`  
  - `src/rune_decrypter_prime/scoring/span_hamming/__init__.py`  
  - `src/rune_decrypter_prime/scoring/span_hamming/calibrated_assets.py`  
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py`

### `tools/benchmarks/periodic_sub_trans`
- only_local: 99
- only_network: 1
- changed_common: 7
- network-only:  
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner - Copy.py` (ignore)
- changed:  
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`  
  - `tools/benchmarks/periodic_sub_trans/common/__init__.py`  
  - `tools/benchmarks/periodic_sub_trans/common/bench_solve_periodic_columnar_kaeding.py`  
  - `tools/benchmarks/periodic_sub_trans/common/paths.py`  
  - `tools/benchmarks/periodic_sub_trans/no_wli/README.md`  
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`  
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`

### `tests`
- only_local: 50
- only_network: 17
- changed_common: 14
- high-value network-only tests to port:  
  - `tests/scoring/test_hamming_dictionary_policy_assets.py`  
  - `tests/scoring/word_ngrams/test_in_memory.py`  
  - `tests/scoring/word_ngrams/test_sqlite_model.py`  
  - `tests/scoring/span_hamming/test_ecdf_interp.py`  
  - `tests/scoring/span_hamming/test_lm_assets_v2.py`  
  - `tests/scoring/span_hamming/test_lm_robustness_smoke.py`  
  - `tests/tools/test_no_wli_word_ngram_report_helpers.py`  
  - plus hard-case/report policy tests under `tests/scoring/span_hamming/*` and `tests/tools/test_report_*`

## 2) Ownership decision (integration policy)

### Take from local (platform authority)

- No-WLI modular runner architecture and StageEngine ecosystem under `tools/benchmarks/periodic_sub_trans/**`.
- Campaign/run config structure and schedule/apply scaffolding.
- Path/privacy guardrails and repo-relative defaults.
- Scorer report infrastructure:
  - `src/rune_decrypter_prime/scoring/scorer_report.py`
  - `src/rune_decrypter_prime/scoring/scorer_report_builder.py`
  - `tools/benchmarks/periodic_sub_trans/common/scorer_sidecar.py`
- Torch backend split modules under `src/rune_decrypter_prime/scoring/torch_backend/*`.
- Objective-normalization and existing parity/JSON-safe contracts.

### Take from network (additive capability)

- Dictionary policy core and resolver:
  - `src/rune_decrypter_prime/core/hamming_dictionary_policy.py`
  - `src/rune_decrypter_prime/scoring/hamming/dictionary_assets.py`
- Span-hamming ECDF/LM utility additions:
  - `src/rune_decrypter_prime/scoring/span_hamming/ecdf_interp.py`
  - `src/rune_decrypter_prime/scoring/span_hamming/lm_assets_v2.py`
- Word-ngram judge stack:
  - `src/rune_decrypter_prime/scoring/word_ngrams/*`
- Associated test suites listed above.

### Manual compose (high-risk, must be curated)

- `src/rune_decrypter_prime/core/config/scoring.py`
- `src/rune_decrypter_prime/api/_resolve.py`
- `src/rune_decrypter_prime/core/problem/runtime.py`
- `src/rune_decrypter_prime/scoring/rune_scorer.py`
- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py`
- `src/rune_decrypter_prime/scoring/base_scorer.py`
- `src/rune_decrypter_prime/scoring/scoring_adapter.py`
- `src/rune_decrypter_prime/scoring/hamming/loader.py`
- `src/rune_decrypter_prime/scoring/span_hamming/calibrated_assets.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py` (logic-port only, not file overwrite)

## 3) First landing behavior policy (must stay explicit)

- Word-ngram judge is report-only in integrated landing.
- Word-ngram judge defaults to `off` for standard no-WLI runs in slice 1.
- One explicit report-only opt-in profile is shipped for visibility and controlled validation.
- No ranking/promotion/acceptance path may depend on word-ngram signal in landing slice 1.
- Span-hamming LM plumbing is included in slice 1, but `span_hamming_lm_weight` default stays `0.0`.
- Existing local StageEngine/campaign schedule behavior stays authoritative.
- Determinism/parity expectations from local branch remain hard gates.

## 4) Detailed phased merge plan

## Phase A: Baseline and branch prep

1. Keep local branch as integration base.
2. Import network branch as comparison/reference only.
3. Freeze merge checklist and gate criteria before code moves.

Exit criteria:
- Exact file matrix approved (this document).
- Behavioral policy for word-ngram confirmed.

## Phase B: Additive file port (low conflict)

Port network-only additive files first:

- `src/rune_decrypter_prime/core/hamming_dictionary_policy.py`
- `src/rune_decrypter_prime/scoring/hamming/dictionary_assets.py`
- `src/rune_decrypter_prime/scoring/span_hamming/ecdf_interp.py`
- `src/rune_decrypter_prime/scoring/span_hamming/lm_assets_v2.py`
- `src/rune_decrypter_prime/scoring/word_ngrams/__init__.py`
- `src/rune_decrypter_prime/scoring/word_ngrams/in_memory.py`
- `src/rune_decrypter_prime/scoring/word_ngrams/runtime.py`
- `src/rune_decrypter_prime/scoring/word_ngrams/scorer.py`
- `src/rune_decrypter_prime/scoring/word_ngrams/sqlite_model.py`

Exit criteria:
- New modules import cleanly.
- Unit tests for these modules run green.

## Phase C: Config contract composition

Manually compose config surface in `core/config/scoring.py` and alias validation in `api/_resolve.py`.

Required merged fields (minimum):

- `hamming_dictionary_policy`
- `hamming_dictionary_policy_root`
- `span_hamming_assets_dictionary_policy`
- `span_hamming_allow_dictionary_policy_mismatch`
- `span_hamming_lm_assets_json`
- `span_hamming_lm_profile_source`
- `span_hamming_lm_tail_start_index`
- `span_hamming_lm_weight`
- `word_ngram_judge_enabled`
- `word_ngram_judge_sqlite_path`
- `word_ngram_judge_alpha`
- `word_ngram_judge_miss_logp`
- `word_ngram_judge_min_positions`
- `word_ngram_judge_prefix_total_thresholds`

Composition rules:

- Keep local JSON-safe `asdict()` behavior.
- Keep local objective normalization/validation discipline.
- Extend canonical key allowlists in `_resolve.py`; avoid duplicate shadow parsers.
- Keep local assets-root conventions as the primary policy root for dictionary assets.
- If packaged `data/...` fallback is present, it must be secondary and explicit (not a silent default switch).

Exit criteria:
- Config round-trip and validation tests pass.
- Unknown-key errors stay strict.

## Phase D: Scorer engine manual integration

Integrate scoring payload into local scorer architecture:

- `scoring/rune_scorer.py`
- `scoring/torch_rune_scorer.py`
- supporting touched files above.

Keep:

- local platform contracts, local torch backend split, local telemetry base shape.

Port:

- dictionary-policy resolution path for hamming/span-hamming wordlists.
- span-hamming LM blend path.
- word-ngram judge runtime + telemetry production.

Hard rules:

- Do not take network `scoring_adapter.py` behavior that depends on missing `score_tokens(...)` API.
- Do not pull network path shifts that replace local assets-root/privacy behavior unless explicitly approved.

Exit criteria:
- NumPy/Torch scorer parity tests pass.
- Legacy scoring behavior unchanged when new knobs disabled.

## Phase E: Canonical report unification

Extend local report pipeline (not runner glue) to carry new telemetry canonically:

- `scoring/scorer_report.py`
- `scoring/scorer_report_builder.py`
- `tools/benchmarks/periodic_sub_trans/common/scorer_sidecar.py`

Target report sections (inside `details`):

- `details["span_hamming"]`
- `details["word_ngrams"]`
- `details["hamming_dictionary"]`
- optional `details["span_lm"]`

Rules:

- Keep single report object (`ScorerReport`).
- Normalize scorer telemetry in builder, not in runner-specific row extractors.
- For transition safety in slice 1, keep raw telemetry keys plus canonical structured `details`.
- Telemetry pruning is explicitly deferred to a follow-up pass after consumers migrate.

Exit criteria:
- Report JSON remains primitive-safe.
- Sidecar output includes structured sections with stable keys.

## Phase F: Runner logic port into modular architecture

Do not merge network `no_wli/runner.py` wholesale.

Port concepts only:

- word-ngram report config construction (currently `_build_word_ngram_report_cfg` in network monolith)
- report field extraction and scalarization
- optional report-side scoring pass for final artifact rows

Re-home targets (local modular):

- `tools/benchmarks/periodic_sub_trans/no_wli/scoring_experiment_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/scoring_policy.py`
- or report-normalization path near `common/scorer_sidecar.py`

Exit criteria:
- No-WLI orchestration remains modular.
- No regression to monolithic runner coupling.

## Phase G: Test gate and acceptance

Minimum acceptance gates:

1. Report contract
- existing local `test_scorer_report_*` remains green
- new structured sections validated

2. Config contract
- scoring config serialization/validation tests green
- new knobs accepted and typed correctly

3. Determinism/parity
- fixed-seed parity tests for periodic_sub_trans runners remain green
- torch/numpy parity tests remain green
- enabling report-only word-ngram does not alter rankings/promotions
- default word-ngram-off runs remain behaviorally stable vs pre-merge baseline

4. Scoring capability
- network word-ngram unit tests green
- dictionary policy tests green
- span-hamming LM/ecdf tests green

5. Runner integration
- no-WLI campaign/schedule/stage-engine tests green

6. Transition compatibility
- legacy/report scripts consuming raw telemetry continue to run in slice 1
- canonical structured sections (`details["span_hamming"]`, `details["word_ngrams"]`, `details["hamming_dictionary"]`) are present and validated

## 5) Explicit do-not-merge-as-is notes

- `tools/benchmarks/periodic_sub_trans/no_wli/runner - Copy.py`: ignore.
- Network `base_scorer.py` carries large commented legacy block; keep local lean base and port only functional deltas.
- Network `scoring_adapter.py` calls `score_tokens(...)` but scorer implementations do not expose that API; do not adopt directly.
- Network changes in `language_model/paths.py` and `hamming/loader.py` shift defaults to packaged `data/...` with less privacy-safe path messaging; keep local path guardrails unless explicitly changed.

## 6) Iteration checklist (practical order)

1. Additive file import + compile/test smoke.
2. Config and alias contract compose.
3. Rune/Torch scorer composition.
4. Report builder canonicalization.
5. No-WLI modular port of remaining runner-only helper concepts.
6. Test sweep and determinism verification.
7. Slice 2 only: hard-case/report-policy script integration.
8. Slice 2 only: prune redundant raw telemetry keys after consumer migration.

## 7) Locked decisions (from review comments)

1. Dictionary policy root: local assets-root is primary. Packaged `data/...` fallback may exist only as explicit secondary behavior.
2. Word-ngram judge: default `off` for normal no-WLI runs in slice 1; provide explicit report-only opt-in profile.
3. Span-hamming LM: wire now, default `span_hamming_lm_weight = 0.0`.
4. Hard-case/report-policy scripts: defer to slice 2 (after scorer/report contract stabilizes).
5. Local API exports: keep unchanged for this merge; defer API simplification.
6. Telemetry: keep raw + structured `details` in slice 1; prune redundant raw keys in follow-up.

## 8) Deferred items (slice 2)

- Hard-case/report-policy script landing from network branch.
- Telemetry pruning once report consumers migrate to canonical `details`.
- Optional reevaluation of default word-ngram enablement after slice-1 stability window.

## 9) Recommendation

Proceed as a staged port with local branch as base.  
Most risk is concentrated in scorer/config composition and report normalization.  
With the locked decisions above, slice 1 remains conservative and deterministic while still landing the new scoring capability.
