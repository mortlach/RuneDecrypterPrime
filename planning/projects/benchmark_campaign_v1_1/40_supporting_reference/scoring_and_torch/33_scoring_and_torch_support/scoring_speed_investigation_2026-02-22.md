# Scoring Speed Investigation (2026-02-22)

Status: Reference evidence log.

Active planning decisions based on this evidence are tracked in:

- `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`

## Scope
This audit covered the scoring path end-to-end for:

- Core solver runtime (`run(...)` via `DecryptionProblem` + solver base)
- Scoring backends (`RuneScorer`, `RuneScorerTorch`, unified facade)
- Language-model runtime and `_fastlm` usage
- Current benchmark pipelines:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
- Current runic pipelines:
  - `solving/finster/runic_v3_pipeline.py`
  - `solving/finster/runic_z_solve.py`

All findings below are from local repo code and local timing runs only.

## Executive Summary

1. A 10x speed-up is plausible in this repo, but not with the current NumPy `batch_score` implementation.
2. In current NumPy backend, `batch_score` is mostly scalar-in-a-loop, so solver-side batching does not translate to major speedups.
3. Torch backend already benefits strongly from batching (measured 4.9x to 13.3x on scoring workloads in this audit).
4. Scoring is confirmed as dominant in hot runs (measured ~95% of wall-time in a representative NumPy kaeding run).
5. Large benchmark/runic loops still do repeated `decrypt_single + scorer.score` and are good batching targets at the caller level.

## Verified Pipeline Path

### Core solver path is batch-oriented

- Solvers call `_score_batch(...)` for candidate populations:
  - `src/rune_decrypter_prime/solvers/ga.py:192`, `src/rune_decrypter_prime/solvers/ga.py:251`
  - `src/rune_decrypter_prime/solvers/beam.py:290`, `src/rune_decrypter_prime/solvers/beam.py:305`
  - `src/rune_decrypter_prime/solvers/sa.py:72`, `src/rune_decrypter_prime/solvers/sa.py:120`
  - `src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py:119`
- Runtime prefers scorer batch APIs:
  - `src/rune_decrypter_prime/core/problem/runtime.py:500`
  - `src/rune_decrypter_prime/core/problem/runtime.py:551`
- Cipher decrypt supports true batch keys:
  - `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:166`
  - `src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py:200`
  - `src/rune_decrypter_prime/ciphers/periodic_substitution_cipher.py:138`

### NumPy backend: batch API exists, but loop-based

- `RuneScorer.batch_score(...)` loops over candidates and calls `self.score(...)` each time:
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:861`
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:913`
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:915`
- `batch_score_with_raw(...)` is similarly loop-based:
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:937`
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:951`
  - `src/rune_decrypter_prime/scoring/rune_scorer.py:958`

### Torch backend: true batch scoring path

- `RuneScorerTorch.batch_score(...)` builds `[B,L]` and calls `_score_batch_impl(...)`:
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:1122`
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:1157`
- `score(...)` delegates to batch with singleton input:
  - `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:1159`

### LM layer is accelerated and batch-capable

- `_fastlm` is imported and used by `LanguageModelPrime`:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:18`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:140`
- Runtime calls batch native methods:
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:519`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:520`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:521`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:556`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:557`
  - `src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py:558`
- Local module is present and importable:
  - `src/rune_decrypter_prime/scoring/language_model/_fastlm.cp311-win_amd64.pyd`

## Measured Evidence (Local)

## 1) Scalar vs batch scorer calls (`pct.logp.win10`, no-WLI, L=452)

Command result:

- Backend `numpy`:
  - `B=32`: scalar `0.0632s`, batch `0.0589s`, speedup `1.07x`
  - `B=64`: scalar `0.1233s`, batch `0.1273s`, speedup `0.97x`
- Backend `torch`:
  - `B=32`: scalar `0.2370s`, batch `0.0481s`, speedup `4.92x`
  - `B=64`: scalar `0.5198s`, batch `0.0837s`, speedup `6.21x`

Interpretation: NumPy batch currently gives little/no gain; Torch batch gives large gain.

## 2) Scalar vs batch scorer calls (with WLI enabled, B=32, L=452)

Command result:

- Backend `numpy`: scalar `0.1307s`, batch `0.1325s`, speedup `0.99x`
- Backend `torch`: scalar `0.4190s`, batch `0.0642s`, speedup `6.53x`

Interpretation: same pattern with WLI; batching benefit is currently backend-dependent.

## 3) End-to-end `run(...)` kaeding timing with telemetry

Controlled run (`periodic_substitution`, same eval budget):

- `impl=numpy`
  - wall `102.262s`
  - evals `40839`
  - `score_time_s=97.257`
  - `decrypt_time_s=4.657`
  - scoring share of wall: `95.11%`
- `impl=torch`
  - wall `21.218s`
  - evals `40839`
  - `score_time_s=16.638`
  - `decrypt_time_s=4.252`
  - scoring share of wall: `78.41%`

Interpretation: scoring is the dominant cost in current NumPy runs; switching backend alone produced ~4.8x wall speedup in this controlled case.

## 4) Runner-style candidate loop (`decrypt_single + score`) vs true batch

Controlled `periodic_columnar` candidate scoring (`B=256`, `p=13`, `c=10`, no-WLI):

- `impl=numpy`
  - scalar loop total `0.5117s`
  - batch decrypt + batch score `0.4831s`
  - speedup `1.06x`
- `impl=torch`
  - scalar loop total `1.5158s`
  - batch decrypt + batch score `0.1138s`
  - speedup `13.33x`

Interpretation: caller-level batching gives huge wins only when scorer backend can exploit batch efficiently.

## Caller-Side Scalar Scoring Hotspots (Batching Targets)

### `no_wli` benchmark pipeline

- Stage-1 archive scoring in loop:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:922`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:927`
- Stage-2 exact pass1/pass2 scalar scoring loops:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1096`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1100`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1157`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1162`
- Stage-2 hybrid post-score:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1234`
- Stage-2 top-k judge rescoring:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1312`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1322`
- Stage-3 diagnostics rescoring:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1526`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:1580`

### `col_then_sub` benchmark pipeline

- Stage-1 archive scoring in loop:
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1627`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1632`
- Stage-1 hard rerank loop:
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1702`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1706`
- Stage-2 exact pass1/pass2 scalar loops:
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1874`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1878`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1908`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:1914`
- Stage-2 hybrid post-score:
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:2021`

### `sub_then_col` benchmark pipeline

- Column probe scalar scoring loop:
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py:945`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py:953`
- Stage-B full scoring loop:
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py:1080`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py:1092`

### Runic pipelines

- `runic_z`:
  - stage1 candidate scoring loop: `solving/finster/runic_z_solve.py:398`, `solving/finster/runic_z_solve.py:403`
  - stage2 exact scoring loop: `solving/finster/runic_z_solve.py:532`, `solving/finster/runic_z_solve.py:536`
- `runic_v3`:
  - exact tail permutation loop scalar scoring: `solving/finster/runic_v3_pipeline.py:1445`, `solving/finster/runic_v3_pipeline.py:1452`

### Seed utilities (benchmark and core)

- Scalar score-heavy loops in seed refinement/ranking:
  - `src/rune_decrypter_prime/utils/seed_utils_periodic_columnar.py:453`
  - `src/rune_decrypter_prime/utils/seed_utils_periodic_columnar.py:467`
  - `src/rune_decrypter_prime/utils/seed_utils_periodic_columnar.py:553`

## Why "10x" Is Plausible Here

It is plausible under this combination:

1. Use a backend with real batch acceleration (`torch` path measured here).
2. Convert caller loops from `decrypt_single + score` into chunked `decrypt(batch_keys) + batch_score(batch_plaintexts)`.
3. Keep candidate counts high enough per batch to amortize Python overhead.

Measured evidence in this repo already reached:

- ~13.3x on a runner-style candidate scoring workload (Torch, B=256)
- ~4.8x wall-clock on an end-to-end kaeding run with same eval count

## Why "10x" Is Not Plausible Yet on Current NumPy Path

Current NumPy `batch_score` path is not vectorized across candidates (`score(...)` loop), so caller batching alone gave ~1.0x-1.1x in measurements.

Without changing backend and/or implementing true NumPy batch scoring internals, 10x is not supported by current evidence.

## Recommended Work Plan (Evidence-Driven)

1. Add explicit scorer implementation knob to heavy benchmark/runic profiles (`impl=torch` option), still deterministic seeds.
2. Batch caller loops in benchmark/runic hotspots listed above:
   - Build candidate key arrays in chunks.
   - Batch decrypt once per chunk using cipher batch API.
   - Batch score once per chunk.
3. Implement true vectorized NumPy `RuneScorer.batch_score` / `batch_score_with_raw`:
   - Avoid `for i: self.score(...)`.
   - Reuse aligned windowing and runtime batch calls across candidate dimension.
4. Add telemetry flag/counter when runtime falls back from batch to scalar scoring:
   - Current fallback in `src/rune_decrypter_prime/core/problem/runtime.py:500` and `src/rune_decrypter_prime/core/problem/runtime.py:551` is silent.
5. Add performance regression checks:
   - Keep existing parity tests.
   - Add speed sanity tests for representative `B` and `L` (separate perf-tier marker).

## Notes

- `_fastlm` acceleration is present and importable in this workspace.
- Existing documentation already references backend choice and telemetry:
  - `docs/guides/scoring_deep.md:17`
  - `docs/reference/scoring/language_model/setup_fastlm.md:3`
