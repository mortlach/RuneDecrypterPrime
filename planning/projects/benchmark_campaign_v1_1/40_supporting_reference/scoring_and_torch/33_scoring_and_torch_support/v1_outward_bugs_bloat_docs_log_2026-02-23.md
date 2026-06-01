# V1 Outward Audit Log (Scoring, IO, Community Campaign)

Date: 2026-02-23
Scope:
- `src/rune_decrypter_prime/scoring/**`
- `src/rune_decrypter_prime/io/**`
- `tools/benchmarks/community/**`
- `tools/benchmarks/periodic_sub_trans/**` (runner readiness + duplication)

## Severity Legend
- P0: likely run/campaign blocker
- P1: reliability/data-integrity/privacy risk
- P2: maintainability/bloat risk
- P3: documentation/polish

## Priority Findings

### SCORING-P0-001 - AVG path still constructs ECDF caches eagerly (NumPy + Torch)
- File: `src/rune_decrypter_prime/scoring/rune_scorer.py:169`
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:306`
- Evidence: both scorers build `ECDFCache(...)` unconditionally during init.
- Why this matters: AVG should be ECDF-free at runtime and resilient to missing ECDF assets for non-win10 experiments.
- Fix direction: lazy-init ECDF only in pct/energy code paths.

### COMMUNITY-P0-001 - Campaign helper run-dir detection mismatches current pipeline output layout
- File: `tools/benchmarks/community/_run_single_job.py:268`
- File: `tools/benchmarks/community/_run_single_job.py:270`
- File: `tools/benchmarks/community/_run_single_job.py:275`
- File: `tools/benchmarks/periodic_sub_trans/common/paths.py:42`
- File: `tools/benchmarks/periodic_sub_trans/common/paths.py:44`
- Evidence: helper scans only direct children of `output/tools/benchmarks`, but periodic runners create run dirs under `output/tools/benchmarks/periodic_sub_trans/<flavor>/<run_id>`.
- Risk: helper can pick wrong directory (or fail to find `instances.json`), producing `exception_raised` rows.
- Fix direction: locate run dir by explicit signal (e.g., runner returns path), or recursive search for newest directory containing both `instances.json` and `stages.json` created after job start.

### COMMUNITY-P1-001 - `scorer_schedule` is declared as profile-controlled but is never applied
- File: `tools/benchmarks/community/profile_catalog_v1_1.json:4`
- File: `tools/benchmarks/community/profile_catalog_v1_1.json:23`
- File: `tools/benchmarks/community/config/profile_config.py:293`
- Evidence: catalog notes claim profile-driven scorer tuning; apply function handles overrides but does not consume `profile.scorer_schedule`.
- Risk: profile dimension can be partially inert/misleading, reducing experiment validity.
- Fix direction: either wire `scorer_schedule` into module globals explicitly or remove it from contract and docs.

### COMMUNITY-P1-002 - Bootstrap `--no-venv` path resolution can break command-style python values
- File: `tools/benchmarks/community/bootstrap.py:81`
- File: `tools/benchmarks/community/bootstrap.py:82`
- Evidence: returns `Path(base_python).resolve()` when `use_venv=False`.
- Risk: values like `python`/`python3` are treated as filesystem paths, not command names.
- Fix direction: keep raw executable string for non-venv mode or resolve via `shutil.which`.

### IO-P1-001 - Share-bundle privacy risk via absolute trace paths in JSONL events
- File: `src/rune_decrypter_prime/io/run_logger.py:67`
- File: `src/rune_decrypter_prime/io/run_logger.py:104`
- File: `src/rune_decrypter_prime/io/run_logger.py:108`
- Evidence: paths are `resolve()`d and emitted as absolute strings.
- Risk: leaks local filesystem layout/user info in shared logs.
- Fix direction: emit repo-relative paths in events; keep absolute only in internal process state.

### COMMUNITY-P1-003 - Run resume path validates schema but does not enforce uniqueness/completeness semantics for existing rows
- File: `tools/benchmarks/community/run_shard.py:274`
- File: `tools/benchmarks/community/run_shard.py:275`
- File: `tools/benchmarks/community/run_shard.py:277`
- Evidence: existing rows are schema-validated but duplicates by `job_id` are not explicitly rejected before resume set is built.
- Risk: silent duplicate/partial resume semantics can skew accounting.
- Fix direction: enforce unique existing `job_id`, and emit explicit missing/duplicate counts in run_meta.

### COMMUNITY-P1-004 - Bundle validator allows incomplete bundles to pass as valid
- File: `tools/benchmarks/community/validate_run_bundle.py:109`
- File: `tools/benchmarks/community/validate_run_bundle.py:124`
- File: `tools/benchmarks/community/validate_run_bundle.py:138`
- Evidence: checks result `job_id` subset membership, but does not require all manifest `job_id`s to be present in results.
- Risk: partial runs can be treated as valid inputs for combine/aggregate unless operator notices.
- Fix direction: add strict mode (default true for integration) requiring `result_job_ids == manifest_job_ids`.

### SCORING-P2-001 - `base_scorer.py` contains very large dead commented blocks
- File: `src/rune_decrypter_prime/scoring/base_scorer.py:198`
- File: `src/rune_decrypter_prime/scoring/base_scorer.py:652`
- Evidence: hundreds of commented legacy/alternate implementations in production file.
- Risk: review noise and maintenance drag.
- Fix direction: remove dead commented code; keep history in git.

### SCORING-P2-002 - `ScoringAdapter` appears dead and calls a non-existent scorer API
- File: `src/rune_decrypter_prime/scoring/scoring_adapter.py:25`
- File: `src/rune_decrypter_prime/scoring/scoring_adapter.py:30`
- Evidence: expects `self.scorer.score_tokens(...)`; no scorer in repo implements `score_tokens`.
- Risk: latent runtime failure if used; dead surface area.
- Fix direction: remove adapter or align to current scorer API (`score` / `batch_score`).

### SCORING-P2-003 - Torch scorer still uses `assert` in low-level helper paths
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:88`
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:90`
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:122`
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:124`
- Risk: assertions disappear under optimized execution.
- Fix direction: replace with explicit validation errors.

### SCORING-P2-004 - Unified scorer has broad silent fallbacks + encoding artifacts
- File: `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:1`
- File: `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:92`
- File: `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:101`
- Evidence: mojibake in docstring and many `except Exception: pass` fallbacks around raw score support.
- Risk: silent backend behavior drift and reduced diagnosability.

### COMMUNITY-P2-001 - Runner implementations are heavily duplicated across flavors
- File: `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- File: `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
- File: `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
- Evidence: repeated helper/function structure (`_apply_run_mode`, `_preview_latin`, `_objective_text`, `_extract_top_keys`, etc.) with file sizes ~2060/2394/1379 LOC.
- Risk: fixes must be ported manually across variants; campaign behavior can drift.
- Fix direction: extract shared pipeline harness and keep flavor-specific deltas only.

### IO-P2-001 - Logging adapter contract is brittle versus run_logger API
- File: `src/rune_decrypter_prime/io/logging_adapter.py:17`
- File: `src/rune_decrypter_prime/io/logging_adapter.py:18`
- File: `src/rune_decrypter_prime/io/run_logger.py:116`
- Evidence: adapter calls `run_logger.get_logger(name)` while implementation currently exposes `get_logger()` with no args.
- Risk: path falls through via broad exception; integration intent is unclear.
- Fix direction: define one explicit logger protocol and enforce it.

### SCORING-P3-001 - Stale/contradictory file-level docs
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:3`
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:15`
- File: `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:1115`
- Evidence: header still says only pct/logp implemented, but code now includes AVG path.
- Risk: contributor confusion and incorrect assumptions.

## Campaign Readiness Notes (Code Surface)
- Manifest/shard/combine/aggregate scripts do perform schema validation and deterministic IDs.
- Main remaining readiness risks are integration seams:
  1. runner output discovery in `_run_single_job`
  2. profile contract mismatch (`scorer_schedule` not wired)
  3. resume/completeness semantics needing stricter checks.

## Suggested Fix Order (Outward)
1. COMMUNITY-P0-001 (run-dir detection) + SCORING-P0-001 (AVG/ECDF separation).
2. COMMUNITY-P1-001/002/003/004 and IO-P1-001.
3. SCORING-P2-001/002/003/004 and COMMUNITY-P2-001.
4. P3 doc cleanup and encoding normalization.

## Extended Findings (API, Utils, Core, KeyOps/Ciphers/Solvers)

### UTILS-P1-001 - `Runeglish` RTL encoding path breaks n-gram tokenisation semantics
- File: `src/rune_decrypter_prime/utils/runeglish.py:179`
- File: `src/rune_decrypter_prime/utils/runeglish.py:212`
- File: `src/rune_decrypter_prime/utils/runeglish.py:227`
- Evidence: RTL path reverses raw text before tokenisation and then reverses tokens; this does not preserve trigram/bigram token units and can change rune length/content.
- Local repro (`PYTHONPATH=src`):
  - `THE` -> LTR `[2, 18]`, RTL `[16, 8, 18]`
  - `THING` -> LTR `[2, 21]`, RTL `[16, 8, 10, 9, 6]`
- Risk: wrong plaintext/ciphertext encoding in RTL workflows (tutorials, benchmark text generation, Hamming RTL dictionaries).
- Fix direction: tokenise canonical word once, then reverse token sequence for RTL; do not reverse raw string first.

### API-P1-001 - `foursquare` wrapper is currently non-runnable
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:362`
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:368`
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:372`
- File: `src/rune_decrypter_prime/ciphers/generic_map_cipher.py:127`
- Evidence: wrapper registers a 4-argument function under `user_map3`, but `user_map3` runtime calls `f(pt, k1, k2)`.
- Local repro (`PYTHONPATH=src`): `RunAPI.run(...)` with `by_name.cipher_with_key("foursquare")` raises `TypeError: ... missing 1 required positional argument: 'k2'`.
- Risk: advertised wrapper path fails immediately when users try it.
- Fix direction: either remove/disable wrapper for v1 or implement correct key/cipher contract (likely dedicated digraph cipher, not `user_map3`).

### API-P1-002 - `hill` wrapper points to a cipher that is not registered
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:207`
- File: `src/rune_decrypter_prime/api/wrappers/registry.py:344`
- File: `src/rune_decrypter_prime/ciphers/__init__.py:13`
- Evidence: wrapper builds `name="hill"` config, but shipped cipher registry imports do not register a `hill` cipher.
- Local repro (`PYTHONPATH=src`): `RunAPI.run(...)` with `by_name.cipher_with_key("hill")` raises `KeyError: "Unknown cipher 'hill'"`.
- Risk: broken user entrypoint; docs/tutorial hints about hill paths cannot execute on this branch.
- Fix direction: either register a supported hill cipher end-to-end or remove/hide the wrapper from public API.

### CORE-P2-001 - `core/config.py` shim has large dead commented code blocks
- File: `src/rune_decrypter_prime/core/config.py:41`
- File: `src/rune_decrypter_prime/core/config.py:133`
- File: `src/rune_decrypter_prime/core/config.py:199`
- File: `src/rune_decrypter_prime/core/config.py:280`
- Evidence: hundreds of lines of commented historical implementations remain in a compatibility shim.
- Risk: maintenance drag, reviewer noise, and confusion about source of truth vs dead code.
- Fix direction: keep only re-export shim; delete commented legacy blocks.

### CORE-P2-002 - `DecryptionProblem` runtime object is too monolithic and exception-heavy
- File: `src/rune_decrypter_prime/core/problem/runtime.py:47`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:631`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:686`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:882`
- File: `src/rune_decrypter_prime/core/problem/runtime.py:971`
- Evidence: one 1200+ LOC class handling config normalization, keyops building, interruptor logic, crib filtering, degeneracy resolution, decrypt/score dispatch, telemetry, and many broad catch/fallback sites.
- Risk: high regression surface; subtle behavior drift between code paths is hard to reason about and test.
- Fix direction: split into focused collaborators (key handling, candidate resolution, scoring dispatch, telemetry counters) with explicit contracts.

### CORE-P2-003 - Device normalization silently coerces unknown strings to CPU
- File: `src/rune_decrypter_prime/core/types.py:142`
- Evidence: `ensure_device(...)` returns `Device.CPU` for any non-`cuda*`/`gpu` input.
- Risk: user typos or config mistakes silently change run mode; harder debugging of expected CUDA paths.
- Fix direction: accept explicit aliases only and raise on unknown values.

### API-P2-001 - `pipeline_helpers.py` uses broad exception swallowing in core normalization path
- File: `src/rune_decrypter_prime/api/pipeline_helpers.py:35`
- File: `src/rune_decrypter_prime/api/pipeline_helpers.py:100`
- File: `src/rune_decrypter_prime/api/pipeline_helpers.py:216`
- Evidence: many `except Exception: pass` blocks around key/plaintext/ciphertext normalization and metadata attachment.
- Risk: malformed state can be silently propagated to outputs/logs, reducing diagnosability.
- Fix direction: narrow exceptions and attach explicit warning fields when recovery paths are used.

### API-P2-002 - API design docs are out of sync with implementation
- File: `src/rune_decrypter_prime/api/README.txt:25`
- File: `src/rune_decrypter_prime/api/README.txt:26`
- File: `src/rune_decrypter_prime/api/pipeline.py:13`
- Evidence: README states API should not talk directly to solvers/scorers, but pipeline imports and calls Stage-2 engine directly.
- Risk: contributor confusion and wrong layering assumptions during refactors.
- Fix direction: update README to current architecture, or reintroduce an adapter layer if that separation is still desired.

### KEYOPS-P2-001 - Runtime-critical validation still relies on `assert`
- File: `src/rune_decrypter_prime/core/engine/builders.py:35`
- File: `src/rune_decrypter_prime/keyops/vector.py:121`
- File: `src/rune_decrypter_prime/keyops/permutation_ops.py:269`
- File: `src/rune_decrypter_prime/keyops/composite.py:472`
- File: `src/rune_decrypter_prime/solvers/solver_base.py:559`
- Evidence: key/device invariants use assertions in non-test runtime code.
- Risk: checks disappear under optimized execution.
- Fix direction: replace with explicit `ValueError`/`TypeError` checks.

### TESTS-P2-001 - Wrapper test coverage misses broken public wrappers
- File: `tests/api/test_periodic_wrappers.py:1`
- File: `tests/tutorials/test_future_presets.py:22`
- File: `tests/tutorials/test_crib_drag_api.py:136`
- Evidence: API wrapper tests cover periodic builders only; hill tutorial tests explicitly skip when hill is not registered, so wrapper breakages can persist unnoticed.
- Risk: user-facing wrappers (`by_name`) can regress without CI failure.
- Fix direction: add a lightweight smoke test over the wrapper registry (`by_name._REG`) that at least validates each wrapper can materialise into a runnable cipher config or is explicitly marked experimental.

### UTILS-P2-001 - `runeglish.py` still has duplicate `rune_to_latin` definitions
- File: `src/rune_decrypter_prime/utils/runeglish.py:68`
- File: `src/rune_decrypter_prime/utils/runeglish.py:73`
- File: `src/rune_decrypter_prime/utils/runeglish.py:247`
- Evidence: second definition overwrites first; TODO acknowledges ambiguity.
- Risk: unclear contract and easy future regressions in transliteration utilities.
- Fix direction: keep one canonical implementation and preserve compatibility via explicit alias.

### CORE-P3-001 - Minor duplication/polish issue in config module
- File: `src/rune_decrypter_prime/core/config/cipher.py:4`
- File: `src/rune_decrypter_prime/core/config/cipher.py:5`
- Evidence: duplicate `from __future__ import annotations`.
- Risk: low; polish/consistency issue.
- Fix direction: remove duplicate import.

## Additional Findings (Telemetry + LP Data + Scoring Facade)

### TELEMETRY-P1-001 - `dump_telemetry` can merge distinct runs into the same file
- File: `src/rune_decrypter_prime/telemetry/pipeline.py:103`
- File: `src/rune_decrypter_prime/telemetry/pipeline.py:104`
- File: `src/rune_decrypter_prime/telemetry/pipeline.py:105`
- Evidence: output filename uses second-resolution timestamp (`run-YYYYMMDD-HHMMSS.jsonl`) and always appends.
- Local repro (`PYTHONPATH=src`): two immediate calls returned the same path:
  - `output\\tmp_tel_test\\run-20260222-204405.jsonl`
  - `output\\tmp_tel_test\\run-20260222-204405.jsonl`
- Risk: cross-run event mixing during concurrent/rapid campaign runs; harder data lineage.
- Fix direction: include higher-resolution/unique suffix (e.g. ns timestamp + pid/uuid) or require caller-provided run id.

### TELEMETRY-P1-002 - Permutation summary accepts inconsistent permutation length metadata
- File: `src/rune_decrypter_prime/telemetry/pipeline.py:34`
- File: `src/rune_decrypter_prime/telemetry/pipeline.py:43`
- File: `src/rune_decrypter_prime/telemetry/pipeline.py:79`
- Evidence: `_perm_summary` hashes provided indices but records `length` from external `ciphertext_len` without validating parity.
- Local repro (`PYTHONPATH=src`): `_perm_summary([0,1,2], 5)` returns `{"kind":"custom","length":5,...}`.
- Risk: telemetry can report a hash for one permutation but a length for another, weakening integrity checks.
- Fix direction: validate `len(indices) == ciphertext_len` for custom permutations and raise on mismatch.

### DATA-P1-001 - `lp_api_example.py` is not runnable as shipped
- File: `src/rune_decrypter_prime/data/liber_primus/lp_api_example.py:2`
- File: `src/rune_decrypter_prime/data/liber_primus/lp_api_example.py:4`
- Evidence: uses non-package import (`from lp_transcript import LPTranscript`) and cwd-relative transcript path.
- Local repro (`PYTHONPATH=src`): running module path raises `ModuleNotFoundError: No module named 'lp_transcript'`.
- Risk: first-touch data API example fails immediately for contributors.
- Fix direction: use package import (`from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript`) and resolve transcript path from `__file__`.

### DATA-P1-002 - `_find_subsequence` gives false negatives for list inputs
- File: `src/rune_decrypter_prime/data/liber_primus/lp_master.py:196`
- File: `src/rune_decrypter_prime/data/liber_primus/lp_master.py:202`
- Evidence: converts needle to tuple, then compares `haystack_slice == needle_tuple`; list slices never equal tuples.
- Local repro (`PYTHONPATH=src`):
  - `_find_subsequence((1,2,3,4),(2,3)) -> 1`
  - `_find_subsequence([1,2,3,4],[2,3]) -> None`
- Risk: helper signature advertises `Sequence[int]`, but behavior depends on concrete sequence type.
- Fix direction: compare like-for-like (`tuple(haystack[i:i+len(needle)]) == needle_tuple`).

### SCORING-P1-001 - `UnifiedRuneScorer` silently masks raw-score failures
- File: `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:88`
- File: `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:92`
- File: `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:98`
- File: `src/rune_decrypter_prime/scoring/unified_rune_scorer.py:101`
- Evidence: broad exception catch in `batch_score_with_raw`/`score_with_raw` falls back to `raw := pct` instead of surfacing failure.
- Local repro (`PYTHONPATH=src` with backend methods raising): methods returned `(pct, pct)` with no error.
- Risk: benchmark analysis can consume fabricated raw values and conclude false scorer parity.
- Fix direction: emit explicit warning/error channel (or raise) when raw path fails; only fallback when backend explicitly declares no raw support.

### TESTS-P2-002 - Missing regression tests for telemetry collision and LP example entrypoint
- File: `tests/telemetry/test_telemetry_off_guard.py:10`
- File: `tests/telemetry/test_pipeline_block_itp.py:11`
- File: `tests/data/test_lp_master_transcript.py:34`
- Evidence: current tests cover telemetry shape/off-switch and LP matching, but do not test per-run dump file uniqueness or runnable `lp_api_example.py`.
- Risk: campaign logging/data-helper regressions can pass CI.
- Fix direction: add (1) `dump_telemetry` uniqueness test under rapid repeated calls and (2) lightweight run-path smoke test for `lp_api_example.py`.

### COMMUNITY-P1-005 - `resume=False` still appends to previous `results.jsonl`
- File: `tools/benchmarks/community/run_shard.py:86`
- File: `tools/benchmarks/community/run_shard.py:274`
- File: `tools/benchmarks/community/run_shard.py:339`
- Evidence: run bundle path is deterministic (`campaign_id + runner_id + shard stem`); when `resume=False`, old rows are not loaded for skipping, but `results.jsonl` is still opened in append mode.
- Local repro (`PYTHONPATH=src`, fake runner): two consecutive runs with `resume=False` produced `rows_after_two_resume_false_runs 2` for a one-job shard.
- Risk: accidental duplicate rows and ambiguous accounting in shared run bundles.
- Fix direction: when `resume=False`, either truncate/archive prior bundle outputs or create a fresh bundle path with a run timestamp/uuid.

### COMMUNITY-P1-006 - `run_shard` does not enforce row identity against the scheduled job
- File: `tools/benchmarks/community/run_shard.py:322`
- File: `tools/benchmarks/community/run_shard.py:333`
- File: `tools/benchmarks/community/run_shard.py:339`
- Evidence: returned row is schema-validated, but not checked for exact equality on identity keys (`job_id`, `campaign_id`, `git_sha`, period/columns/order/profile/run_seed/replicate_idx/config_fingerprint`) versus the manifest job being processed.
- Local repro (`PYTHONPATH=src`, fake runner returning `job_id='job_other_9999'`): shard accepted and wrote `written_job_id job_other_9999`.
- Risk: helper or runner bugs can silently mis-attribute results to the wrong job.
- Fix direction: enforce field-by-field identity match before writing; coerce to `_default_error_row(..., stop_reason='invalid_config')` on mismatch.

### COMMUNITY-P1-007 - Resume can skip jobs from an older git revision
- File: `tools/benchmarks/community/run_shard.py:275`
- File: `tools/benchmarks/community/run_shard.py:277`
- File: `tools/benchmarks/community/run_shard.py:316`
- Evidence: existing rows are only schema-validated, then used to build `completed_job_ids`; no check that existing rows match current `campaign_id`/`git_sha`.
- Local repro (`PYTHONPATH=src`):
  - first run wrote row with `git_sha=1111111`
  - second run changed campaign+manifest git sha to `2222222`
  - output: `resume_skips 1 processed 0`, persisted row remained `row_git_sha 1111111`
- Risk: stale results from an older code revision can block fresh jobs and poison campaign integration.
- Fix direction: on resume, require existing rows to match current campaign/git (and optionally config fingerprint); otherwise fail fast or move old results aside.

### TESTS-P2-003 - Run-shard tests miss non-resume and stale-resume integrity paths
- File: `tests/community/test_run_shard_v1_1.py:69`
- File: `tests/community/test_run_shard_v1_1.py:116`
- Evidence: current tests cover schema-valid write and `resume=True` skip behavior, but not `resume=False` bundle reuse or git-sha drift scenarios.
- Risk: data-integrity regressions in campaign execution can pass CI unnoticed.
- Fix direction: add tests for:
  1. `resume=False` re-run should not append duplicate historical rows,
  2. resume should reject/segregate existing rows with mismatched git_sha/campaign metadata,
  3. run_job output identity mismatch should be rejected.

### COMMUNITY-P0-002 - `col_then_sub` runner filters out non-p10 community tiers by default
- File: `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:102`
- File: `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:639`
- File: `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:645`
- File: `tools/benchmarks/community/_run_single_job.py:107`
- Evidence: runner default `TIERS_PERIOD_SWEEP="p10_only"` is applied in `_apply_runtime_overrides()` after community helper injects a single tier from job manifest.
- Local repro (`PYTHONPATH=src`):
  - `_configure_module_for_campaign_job(...)` with `period=7` sets tier `community_col_then_sub_p7_c3_l1234`
  - subsequent `_apply_run_mode(); _apply_runtime_overrides()` raises:
    `ValueError Tier selection is empty after overrides; adjust TIERS_REGEX_OVERRIDE / TIERS_PERIOD_SWEEP / TIERS_MIN_COLUMNS`
- Risk: col-then-sub campaign jobs for non-p10 periods fail as `exception_raised`, distorting campaign coverage.
- Fix direction: force `TIERS_PERIOD_SWEEP="none"` in campaign mode (or skip sweep filtering when tiers are explicitly injected).

### COMMUNITY-P1-008 - `PIPELINE_DEFAULT` sentinel still clears Stage-3 per-column gates
- File: `tools/benchmarks/community/config/profile_config.py:298`
- File: `tools/benchmarks/community/config/profile_config.py:300`
- File: `tools/benchmarks/community/config/profile_config.py:302`
- Evidence: even when `stage3_gating.full_entry_score/probe_entry_score` are `PIPELINE_DEFAULT`, function still resets `STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS` and `STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS` to `{}`.
- Local repro (`PYTHONPATH=src`, SimpleNamespace module):
  - before: `STAGE3_*_BY_COLUMNS={3:...}`
  - after apply with defaults sentinel: both maps become `{}`
- Risk: profile intending “leave pipeline defaults intact” can silently erase tuned per-column gates.
- Fix direction: only clear per-column maps when an explicit non-default stage3 gating override is applied.

### RUNNERS-P2-001 - Periodic benchmark runners are monolithic and heavily duplicated
- File: `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- File: `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
- File: `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
- Evidence: current sizes are ~2197 LOC, ~2523 LOC, and ~1479 LOC with repeated stage orchestration, reporting, checkpointing, and global knob mutation patterns.
- Risk: fixes drift across runners, high review load, and inconsistent behavior between campaign paths.
- Fix direction: extract shared runner kernel (stage loop/checkpoint/report/manifest), keep per-flavor differences as small config+strategy modules.

## Additional Findings (Ciphers + KeyOps + Solvers Pass)

### SOLVERS-P0-001 - GA fallback crossover collapses genes to binary values
- File: `src/rune_decrypter_prime/solvers/ga.py:74`
- File: `src/rune_decrypter_prime/solvers/ga.py:105`
- Evidence: fallback branch (when `keyops.recombine` is unavailable) uses bitwise masking:
  - `children = (a & (mask == 0)) | (b & (mask == 1))`
  - this performs bitwise AND with boolean arrays, producing `{0,1}` values instead of selecting parent genes.
- Local repro (`PYTHONPATH=src` with dummy keyops lacking recombine):
  - parent values: `[5,6,7,8,10,11,12,13]`
  - child sample rows: `[[0,0,1,0], [1,0,0,1], ...]`
  - child unique values: `[0,1]`
- Risk: GA can catastrophically degrade search quality for any key family that falls back to this path.
- Fix direction: replace fallback with `np.where(mask == 0, a, b)` (or equivalent typed selection).

### KEYOPS-P0-001 - `VectorKeyOps` cannot represent moduli >255 due hard-coded `uint8`
- File: `src/rune_decrypter_prime/keyops/vector.py:76`
- File: `src/rune_decrypter_prime/keyops/vector.py:81`
- File: `src/rune_decrypter_prime/keyops/vector.py:83`
- File: `src/rune_decrypter_prime/keyops/vector.py:85`
- File: `src/rune_decrypter_prime/keyops/vector.py:115`
- Evidence: `normalize/random/recombine` and population helpers cast to `np.uint8` unconditionally.
- Local repro (`PYTHONPATH=src`):
  - `VectorKeyOps(K=4, mod=841).normalize([300,511,840,129]) -> [44,255,72,129]`
  - expected modulo-841 values are `[300,511,840,129]`
  - `validate([300,511,840,129])` passes, because it first casts to uint8.
- Risk: any vector-key domain above 255 is silently truncated, invalidating key search and reproducibility.
- Fix direction: use `KEY_DTYPE` (or dynamic dtype based on `mod`) across vector keyops and validation.

### CIPHERS-P0-001 - `GenericMapCipher` truncates key-value domain for `user_map3`
- File: `src/rune_decrypter_prime/ciphers/generic_map_cipher.py:86`
- File: `src/rune_decrypter_prime/ciphers/generic_map_cipher.py:214`
- File: `src/rune_decrypter_prime/ciphers/generic_map_cipher.py:226`
- File: `src/rune_decrypter_prime/ciphers/generic_map_cipher.py:247`
- File: `src/rune_decrypter_prime/ciphers/generic_map_cipher.py:253`
- Evidence: `user_map3` advertises `mod = A*A` (for A=29 => 841), but core encrypt/decrypt cast keys to `uint8`.
- Local repro (`PYTHONPATH=src`):
  - with `A=29`, key `300` and key `44` produce identical ciphertext outputs.
  - expected outputs differ because key 300 encodes `(k1,k2)=(10,10)` while 44 encodes `(1,15)`.
- Risk: `user_map3` key-space collapses; distinct keys alias to same behavior.
- Fix direction: consume key arrays as `KEY_DTYPE` (or at least `int16`) in generic-map core paths.

### SOLVERS-P1-002 - `_slow_evaluate_keys` fallback calls cipher decrypt with wrong signature
- File: `src/rune_decrypter_prime/solvers/solver_base.py:599`
- File: `src/rune_decrypter_prime/solvers/solver_base.py:612`
- File: `src/rune_decrypter_prime/solvers/solver_base.py:614`
- Evidence: fallback calls `self.problem.cipher.decrypt(self.problem.ciphertext, k)` positionally, but canonical ciphers expose keyword-only decrypt (`decrypt(*, ciphertext, key, ...)`).
- Local repro (`PYTHONPATH=src`, dummy cipher with keyword-only signature):
  - `TypeError: DummyCipher.decrypt() takes 1 positional argument but 3 were given`
- Risk: if problem hooks are missing and solver falls back, evaluation crashes in a hard-to-debug path.
- Fix direction: use keyword arguments consistently in fallback (`decrypt(ciphertext=..., key=...)`).

### CIPHERS-P1-001 - shared `_as_u8` coercion silently wraps/truncates values
- File: `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:354`
- File: `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:357`
- Evidence: `_as_u8` always uses `np.asarray(..., dtype=np.uint8)` without range/type guards.
- Local repro (`PYTHONPATH=src`):
  - `_as_u8([300,-1], ...) -> [44,255]`
  - `_as_u8([1.9,2.1], ...) -> [1,2]`
- Risk: malformed plaintext/ciphertext/key material can be silently accepted and transformed, corrupting experiments.
- Fix direction: validate integer/range before casting, and fail fast on lossy coercion.

### CIPHERS-P1-002 - Columnar key path accepts overflow/float keys after silent coercion
- File: `src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py:82`
- File: `src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py:93`
- File: `src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py:102`
- File: `src/rune_decrypter_prime/ciphers/columnar_transposition_cipher.py:149`
- Evidence: columnar decrypt/encrypt convert keys via `_as_u8` before validation.
- Local repro (`PYTHONPATH=src`):
  - key `[0.2,1.8,2.2,3.0,4.0]` accepted and treated as `[0,1,2,3,4]`
  - key `[0,1,2,3,260]` accepted and treated as `[0,1,2,3,4]`
- Risk: non-integer or overflow keys can pass as valid permutations, hiding input/config errors.
- Fix direction: parse keys as signed/integer dtype first, validate exact integer semantics, then cast.

### CIPHERS-P2-001 - `ciphers_pipeline.py` contains a large dead commented duplicate implementation
- File: `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:458`
- File: `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:477`
- File: `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:531`
- File: `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:629`
- Evidence: legacy full class body is retained as comments after live implementation.
- Risk: review noise and higher chance of fixing the wrong block during maintenance.
- Fix direction: remove dead commented implementation; rely on VCS history.

### TESTS-P2-004 - coverage gaps for high-domain keys and GA fallback behavior
- File: `tests/ciphers/test_user_map3_domain.py:20`
- File: `tests/keyops/test_vector_key_ops.py:16`
- File: `tests/solvers/test_permutation_optimizers.py:14`
- Evidence:
  - `test_user_map3_domain` validates `mod == A*A` with `A=5`, but does not execute encrypt/decrypt with key values >255.
  - vector keyops tests use small moduli (e.g., 29/17/13), so >255 truncation is untested.
  - solver tests exercise permutation paths; no test forces GA recombine fallback branch without `keyops.recombine`.
- Risk: regressions in high-domain key handling and solver fallbacks can ship unnoticed.
- Fix direction: add targeted tests for:
  1. `user_map3` encrypt/decrypt parity with keys >255,
  2. `VectorKeyOps(mod>255)` normalize/random/validate contracts,
  3. GA fallback crossover gene provenance when `recombine` verb is absent.

## Additional Findings (Core Config + KeyOps Semantics Pass)

### KEYOPS-P1-002 - `PermutationKeyOps.validate` accepts negative entries
- File: `src/rune_decrypter_prime/keyops/permutation_ops.py:262`
- File: `src/rune_decrypter_prime/keyops/permutation_ops.py:272`
- File: `src/rune_decrypter_prime/keyops/permutation_ops.py:273`
- Evidence: validation checks `k < K` and uniqueness, but does not enforce `k >= 0`.
- Local repro (`PYTHONPATH=src`):
  - `PermutationKeyOps(K=3).validate([-1,0,1])` passes.
  - `validate([0,1,3])` correctly fails, confirming lower-bound check is the gap.
- Risk: malformed permutation keys can pass explicit validation and then behave unpredictably in downstream indexing.
- Fix direction: add explicit non-negative check before uniqueness/bijection checks.

### CIPHERS-P1-003 - `PeriodicColumnarCipher` does not validate substitution blocks as permutations
- File: `src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py:81`
- File: `src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py:97`
- File: `src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py:100`
- File: `src/rune_decrypter_prime/ciphers/periodic_columnar_cipher.py:121`
- File: `src/rune_decrypter_prime/ciphers/periodic_substitution_cipher.py:29`
- File: `src/rune_decrypter_prime/ciphers/periodic_substitution_cipher.py:98`
- Evidence: periodic-substitution path has `_validate_key_blocks(...)`; periodic-columnar's periodic sub-stage does not.
- Local repro (`PYTHONPATH=src`):
  - periodic-columnar accepted a key where one substitution block had duplicates/missing symbols.
  - decrypt/encrypt executed and returned outputs instead of rejecting invalid key structure.
- Risk: invalid substitution keys can silently propagate into benchmark runs and mask key integrity issues.
- Fix direction: share and enforce the same block-permutation validator used by `PeriodicSubstitutionCipher`.

### CORE-P1-001 - Legacy `interruptors_max` is coerced to exact-count pool search
- File: `src/rune_decrypter_prime/core/config/cipher.py:141`
- File: `src/rune_decrypter_prime/core/config/cipher.py:149`
- File: `src/rune_decrypter_prime/core/config/cipher.py:150`
- Evidence: in legacy-field normalization, `interruptors_max=N` is mapped to `min_count=N, max_count=N`.
- Local repro (`PYTHONPATH=src`):
  - `CipherConfig(..., interruptors_pool=[0,2,4], interruptors_max=2)` yields `interruptors_cfg.min_count=2`, `max_count=2`.
- Risk: callers expecting "up to N" behavior get exact-N behavior, reducing search coverage unexpectedly.
- Fix direction: map legacy `interruptors_max` to `min_count=0, max_count=N` (or document exact-count behavior explicitly and rename field).

### CORE-P2-004 - Config `asdict()` output is not JSON-safe by default
- File: `src/rune_decrypter_prime/core/config/scoring.py:170`
- File: `src/rune_decrypter_prime/core/config/scoring.py:182`
- File: `src/rune_decrypter_prime/core/config/scoring.py:183`
- File: `src/rune_decrypter_prime/core/config/run.py:82`
- File: `src/rune_decrypter_prime/core/config/run.py:86`
- Evidence: scoring config `asdict()` leaves enum/dataclass objects in output (`se_mode`, `objective`), and `RunConfig.asdict()` uses `dataclasses.asdict(self.scorer_params)`.
- Local repro (`PYTHONPATH=src`):
  - `json.dumps(ScoringConfig(...).asdict())` fails with `TypeError: Object of type SeMode is not JSON serializable`.
  - `json.dumps(RunConfig(...).asdict())` fails with same error.
- Risk: any workflow assuming `asdict()` is serialization-ready can fail at runtime.
- Fix direction: route through explicit serializer (`ScoringConfig.asdict()` returning primitive values only) inside `RunConfig.asdict()` and normalize enum/object fields.

### TESTS-P2-005 - Missing regression tests for validation lower-bounds and legacy interruptor semantics
- File: `tests/keyops/test_permutation_key_ops.py:25`
- File: `tests/ciphers/test_periodic_columnar_cipher.py:25`
- File: `tests/core/test_interruptor_wli_guard.py:29`
- Evidence:
  - permutation tests verify bijection structure but do not assert `validate()` rejects negative entries.
  - periodic-columnar tests cover roundtrip behavior but not rejection of invalid substitution blocks.
  - interruptor tests focus on canonical `InterruptorConfig`, not legacy `interruptors_pool` + `interruptors_max` normalization semantics.
- Risk: these edge-case regressions can remain undetected despite broad functional tests.
- Fix direction: add targeted contract tests for:
  1. `PermutationKeyOps.validate` negative input rejection,
  2. periodic-columnar invalid sub-block rejection,
  3. legacy interruptor field translation semantics.

## Additional Findings (Utils + Core Builder Pass)

### UTILS-P1-001 - `_to_ct_indices` emits nested lists and is unusable for frequency counting
- File: `src/rune_decrypter_prime/utils/seed_utils.py:24`
- File: `src/rune_decrypter_prime/utils/seed_utils.py:27`
- Evidence: string path does `Runeglish.rune_to_pos(c)` per character, but `rune_to_pos` already returns a list; output becomes `list[list[int]]`.
- Local repro (`PYTHONPATH=src`):
  - `_to_ct_indices(<3-rune-string>) -> [[0], [1], [2]]`
  - `Counter(_to_ct_indices(...))` raises `TypeError: unhashable type: 'list'`.
- Additional context: helper appears dead/unreferenced (`rg "_to_ct_indices\("` only matches its definition), so the latent bug is currently hidden.
- Fix direction: return flat ints (`extend` behavior or single-pass `Runeglish.rune_to_pos(ct_no_spaces)`) and add direct tests, or remove dead helper.

### UTILS-P1-002 - `rank_alignment_seed` type contract is wider than implementation
- File: `src/rune_decrypter_prime/utils/seed_utils.py:66`
- File: `src/rune_decrypter_prime/utils/seed_utils.py:71`
- Evidence: annotated `CiphertextLike = Union[str, Sequence[int], np.ndarray]`, but implementation unconditionally calls `Runeglish.rune_to_pos(ct)` (string-only).
- Local repro (`PYTHONPATH=src`):
  - `rank_alignment_seed(np.array([0,1,2], dtype=np.uint8))` raises `TypeError: rune_to_pos expects str`.
- Risk: callers using numeric ciphertext (as allowed by signature/docs) hit immediate runtime failure.
- Fix direction: route through a single normalizer that accepts both rune strings and integer sequences, then count from flattened integer symbols.

### CORE-P1-002 - CUDA backend guard in `build_scorer` is implemented as `assert` and is bypassed under `python -O`
- File: `src/rune_decrypter_prime/core/engine/builders.py:33`
- File: `src/rune_decrypter_prime/core/engine/builders.py:35`
- Evidence: backend verification uses `assert dev_name == "cuda"`.
- Local repro:
  - Normal mode (`python`): monkeypatched `select_backend` returning `'cpu'` with `device='cuda'` raises `AssertionError`.
  - Optimized mode (`python -O`): same setup returns a scorer instance; guard is skipped.
- Risk: optimized/interpreted environments can silently proceed with mismatched backend state.
- Fix direction: replace assert with explicit runtime check (`if dev_name != "cuda": raise RuntimeError(...)`).

### CORE-P2-005 - `core/config.py` compatibility shim contains a very large stale commented code payload
- File: `src/rune_decrypter_prime/core/config.py:40`
- File: `src/rune_decrypter_prime/core/config.py:368`
- Evidence: after the intended re-export shim, hundreds of lines of commented legacy config/solution scaffolding remain in production source.
- Risk: review noise, maintenance drift, and higher chance of editing stale blocks by mistake.
- Fix direction: keep shim-only content in this module; remove dead commented payload and rely on git history.

### UTILS-P2-002 - `Runeglish` has duplicate `rune_to_latin` definitions (first is dead)
- File: `src/rune_decrypter_prime/utils/runeglish.py:68`
- File: `src/rune_decrypter_prime/utils/runeglish.py:73`
- File: `src/rune_decrypter_prime/utils/runeglish.py:247`
- Evidence: second definition overwrites first; file-level TODO already acknowledges this.
- Risk: confusing API surface/documentation drift during refactors.
- Fix direction: consolidate into a single implementation and keep signature compatibility via explicit wrapper if needed.

### TESTS-P2-006 - Coverage gaps for newly observed utils/core guard behavior
- File: `tests/tutorials/test_mono_substitution.py:10`
- File: `tests/scoring/test_backend_selection_and_parity.py:30`
- Evidence:
  - tests exercise `make_seeds_from_freq` from rune-string path only; no tests for `rank_alignment_seed` with numeric ciphertext input.
  - backend-selection tests do not assert behavior under optimized interpreter semantics (`assert`-free paths).
- Risk: regressions in seed-utils input contracts and backend guards can ship unnoticed.
- Fix direction: add targeted tests for numeric-sequence seed input handling and replace/assert-free backend guard checks.

## Additional Findings (API Surface Pass)

### API-P1-001 - Invalid `CipherSpec` type annotation breaks runtime type-hint introspection
- File: `src/rune_decrypter_prime/api/specs.py:54`
- Evidence: field is annotated `device: Optional[str, Device]`, which is invalid for `typing.Optional`.
- Local repro (`PYTHONPATH=src`):
  - `typing.get_type_hints(CipherSpec)` raises `TypeError: typing.Optional requires a single type. Got (<class 'str'>, <enum 'Device'>).`
- Risk: tooling/runtime paths that resolve annotations (schema generators, docs, validators) fail unexpectedly.
- Fix direction: replace with `device: Optional[str | Device]` (or `str | Device | None`).

### API-P1-002 - `maps_api.preview` is currently non-functional due invalid `CipherConfig` argument
- File: `src/rune_decrypter_prime/api/maps_api.py:95`
- File: `src/rune_decrypter_prime/api/maps_api.py:131`
- File: `src/rune_decrypter_prime/api/maps_api.py:135`
- Evidence: preview constructs `CipherConfig(..., text_transposition=...)`, but `CipherConfig` has no `text_transposition` parameter.
- Local repro (`PYTHONPATH=src`):
  - `preview([0,1,2], cipher=define_map(function=...), key=KeySpec.const(value=1))`
  - raises `TypeError: CipherConfig.__init__() got an unexpected keyword argument 'text_transposition'`.
- Risk: advertised preview UX path fails before solver/cipher execution.
- Fix direction: pass canonical config field(s) (`encoding_dir` / `initial_text_permutation_indices`) and remove legacy arg.

### API-P1-003 - `double_transposition` wrapper default-key branch calls keyword-only factory incorrectly
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:321`
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:338`
- Evidence: `KeySpec.permutation` is keyword-only (`len=...`), but wrapper calls `KeySpec.permutation(key_len1)` and `KeySpec.permutation(key_len2)`.
- Local repro (`PYTHONPATH=src`):
  - `by_name.cipher_with_key('double_transposition', key_len1=5, key_len2=6, default_key=True)`
  - raises `TypeError: KeySpec.permutation() takes 1 positional argument but 2 were given`.
- Risk: this wrapper path cannot generate default key specs, breaking the intended user entrypoint.
- Fix direction: call with keywords (`KeySpec.permutation(len=key_len1)` / `len=key_len2`).

### API-P2-001 - `api/api.py` is a fully commented dead module
- File: `src/rune_decrypter_prime/api/api.py:1`
- File: `src/rune_decrypter_prime/api/api.py:37`
- Evidence: entire file body is commented-out legacy compatibility code.
- Risk: maintenance noise and confusion about canonical API entrypoints.
- Fix direction: remove file or replace with a minimal explicit compatibility shim (live code only).

### TESTS-P2-007 - API coverage gaps for wrapper/preview regression paths
- File: `tests/ciphers/test_custom_define_map.py:14`
- File: `tests/api/test_normalize.py:126`
- Evidence:
  - current API tests cover map definition and normalization, but do not execute `maps_api.preview(...)`.
  - no coverage for `by_name.cipher_with_key('double_transposition', default_key=True, ...)`.
  - no test exercises `typing.get_type_hints(CipherSpec)` (annotation validity smoke).
- Risk: API entrypoint regressions in preview/wrapper convenience paths can ship unnoticed.
- Fix direction: add small regression tests for preview construction, double-transposition default key creation, and type-hint introspection.

### API-P2-002 - `by_name` class-level type hints are not introspection-safe
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:75`
- File: `src/rune_decrypter_prime/api/wrappers/by_name.py:484`
- Evidence: `_REG` annotation references `"CipherSpec"`/`"KeySpec"` names that are not present in module globals (lazy-import pattern).
- Local repro (`PYTHONPATH=src`):
  - `typing.get_type_hints(by_name)` raises `NameError: name 'CipherSpec' is not defined`.
- Risk: runtime schema/doc tooling that introspects class annotations can fail.
- Fix direction: add `if TYPE_CHECKING:` imports (or simplify `_REG` annotation to avoid unresolved forward refs at runtime).

### TESTS-P2-008 - Missing runtime type-hint smoke checks for API wrapper classes
- File: `tests/api/test_normalize.py:42`
- Evidence: current API tests validate normalizers and map flow but do not run runtime annotation introspection against wrapper/spec classes.
- Risk: annotation regressions (`typing.get_type_hints(...)` failures) can slip through unnoticed.
- Fix direction: add a small API smoke test for `get_type_hints(CipherSpec)` and `get_type_hints(by_name)` (or explicit exclusion policy).

## Campaign Integrity Update (2026-02-27)

### COMMUNITY-P1-001 - Added tamper-evident results chain to run bundles
- Files:
  - `tools/benchmarks/community/_campaign_common.py`
  - `tools/benchmarks/community/run_shard.py`
  - `tools/benchmarks/community/validate_run_bundle.py`
  - `tests/community/test_run_shard_v1_1.py`
  - `tests/community/test_validate_run_bundle_v1_1.py`
  - `tests/community/test_combine_and_aggregate_v1_1.py`
- Change:
  - `run_shard` now writes `results_integrity.jsonl` alongside `results.jsonl`.
  - Each row has a deterministic SHA-256 hash and chained `prev_chain_hash -> chain_hash`.
  - `run_meta.json` now stores `results_integrity` summary (`version`, `hash_algorithm`, `genesis_hash`, `row_count`, `final_chain_hash`).
  - `validate_run_bundle` now requires integrity sidecar and rejects mismatch/tamper.
- Verification status:
  - `tests/community` passes after update.
  - Added explicit tamper regression test (`test_validate_run_bundle_rejects_tampered_results_row`).
- Residual risk:
  - This is tamper-evident, not cryptographic provenance; a malicious actor with full rewrite access can recompute chain.
  - For stronger anti-fake guarantees, next step is organiser-side signed attestations or external digest ledger.

## Status Corrections (2026-02-27)

The sections below were listed as active blockers earlier in this log but are now resolved in code and covered by tests.

### SCORING-P0-001 - AVG path ECDF coupling [Resolved]
- Current status:
  - AVG path is separated from ECDF runtime path.
  - Regression/parity tests exist in:
    - `tests/scoring/test_avg_ecdf_runtime_separation.py`
    - `tests/scoring/test_torch_avg_fulltext_stability.py`
- Note:
  - keep this item closed unless future changes reintroduce ECDF access in AVG paths.

### COMMUNITY-P0-001 - Campaign run-dir detection mismatch [Resolved]
- Current status:
  - Campaign single-job runner now resolves output dirs from flavor-scoped paths under `output/tools/benchmarks/periodic_sub_trans/<flavor>/...`.
  - Legacy broad top-level run-dir guessing path is removed.
- Evidence:
  - `tools/benchmarks/community/_run_single_job.py`
  - `tests/community/test_run_single_job_config_v1_1.py`

### COMMUNITY-P1-003 - Resume integrity semantics [Partially Resolved]
- Current status:
  - Resume now verifies hash-chain integrity of existing rows before appending.
  - Duplicate existing `job_id` enforcement is still not a dedicated explicit error path.
- Evidence:
  - `tools/benchmarks/community/run_shard.py`
  - `tools/benchmarks/community/validate_run_bundle.py`

### COMMUNITY-P1-005 - Absolute machine paths in campaign `run.log` JOB_CMD [Resolved]
- Current status:
  - `JOB_CMD` lines are now sanitized to avoid absolute user/machine paths.
  - temp file arguments are redacted (`<tmp_path>`), and repo-local paths are rendered relative.
  - captured helper stdout/stderr written into `run.log` is also path-sanitized.
- Evidence:
  - `tools/benchmarks/community/run_shard.py`
  - `tests/community/test_run_shard_v1_1.py::test_format_job_cmd_for_log_redacts_absolute_paths`
  - `tests/community/test_run_shard_v1_1.py::test_sanitize_log_text_redacts_absolute_paths`

### COMMUNITY-P0-003 - `sub_then_col` canary job path rendering failure [Resolved]
- Previous failure signature:
  - canary job returned `exception_raised` with:
  - `'<...output\\tools\\benchmarks\\periodic_sub_trans\\sub_then_col\\...>' is not in the subpath of '<...\\tools\\benchmarks>'`
- Root cause:
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py::_repo_root()` returned `Path(__file__).resolve().parents[2]` (`...\\tools\\benchmarks`) instead of repository root.
  - later `run_dir.relative_to(root)` calls then crashed when `run_dir` lived under repo `output/...`.
- Fix:
  - `_repo_root()` now returns `_ROOT` (repo root), matching other runners.
- Evidence:
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
  - `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py::test_sub_then_col_repo_root_matches_repo_root`
  - local 2-job canary recheck completed with `exception_raised_count=0` and valid integrity/schema bundle.

### COMMUNITY-P1-009 - Timeout fallback rows incorrectly forced `fastlm_present=false` [Resolved]
- Previous behavior:
  - when helper subprocess timed out (`time_cap_reached`) or failed before payload, `run_shard` emitted fallback rows with hardcoded `fastlm_present=false`.
  - this made strict validator mode (`require_fastlm_true=True`) fail even when fastlm was actually available.
- Fix:
  - added repo-aware fastlm probe in `run_shard` fallback path.
  - timeout/error fallback rows now carry detected fastlm availability.
- Evidence:
  - `tools/benchmarks/community/run_shard.py`
  - `tests/community/test_run_shard_v1_1.py::test_run_job_with_helper_timeout_preserves_fastlm_detection`
  - local smoke bundle (`time_cap_reached` row) validates with `require_fastlm_true=True`.

### COMMUNITY-P0-002 - `col_then_sub` non-p10 campaign tier filtering [Resolved]
- Previous behavior:
  - campaign jobs for `order=col_then_sub` with non-p10 periods could fail early with:
  - `ValueError: Tier selection is empty after overrides; adjust TIERS_REGEX_OVERRIDE / TIERS_PERIOD_SWEEP / TIERS_MIN_COLUMNS`
- Root cause:
  - runner default `TIERS_PERIOD_SWEEP=\"p10_only\"` was still active in campaign mode.
- Fix:
  - `configure_campaign_run(...)` now forces campaign-safe tier overrides:
    - `TIERS_PERIOD_SWEEP=\"none\"`
    - `TIERS_MIN_COLUMNS=None`
- Evidence:
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
  - `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py::test_col_then_sub_campaign_config_disables_tier_sweep_filters`
  - local full canary matrix (8 jobs) recheck with strict fastlm validation: `error=0`, all rows schema/integrity-valid.

### COMMUNITY-P1-006 - `run_shard` row identity enforcement against scheduled job [Resolved]
- Previous behavior:
  - helper-returned rows were schema-validated, but identity keys were not enforced against manifest job fields.
- Fix:
  - added strict identity check for:
    - `campaign_id, job_id, git_sha, text_fixture_id, period, columns, order, profile_id, run_seed, replicate_idx, config_fingerprint`.
  - mismatches now emit `ROW_IDENTITY_MISMATCH` in `run.log` and are written as `status=error`, `stop_reason=invalid_config` for the scheduled job id.
- Evidence:
  - `tools/benchmarks/community/run_shard.py`
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_marks_identity_mismatch_as_invalid_config`

### COMMUNITY-P1-003 - Resume existing-row integrity semantics [Further Resolved]
- Added resume-time guards:
  - reject duplicate existing `job_id` rows,
  - reject existing rows whose `job_id` is not in current shard,
  - reject existing rows whose identity fields mismatch their manifest job.
- Evidence:
  - `tools/benchmarks/community/run_shard.py`
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_resume_rejects_duplicate_existing_job_ids`
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_resume_rejects_existing_job_not_in_shard`

### COMMUNITY-P1-005 - Non-resume bundle reuse cleanup [Further Resolved]
- Current behavior when `resume=False`:
  - clears `results.jsonl`, `results_integrity.jsonl`, and now also `run.log`/`run_meta.json` before writing fresh outputs.
- Evidence:
  - `tools/benchmarks/community/run_shard.py`
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_resume_false_resets_run_log_and_rows`

### COMMUNITY-CANARY-STATUS - Full-cap matrix canary completed cleanly [Verified]
- Full canary matrix (`8` jobs, real cap `300s/job`) executed via resumable shard passes.
- Final run characteristics:
  - `status_counts={\"unsolved\": 8}`
  - `stop_reason_counts={\"time_cap_reached\": 8}`
  - `error=0`
  - strict bundle validation passed with `require_fastlm_true=True`
  - `fastlm_present=true` on all rows
  - no user-path leak patterns in `run.log` (`C:\\Users\\` absent)
- Bundle:
  - `output/tools/benchmarks/community/local_canary_fullcap_20260228T223633Z/run_bundle__community_bench_canary_v1_1_fullcap_20260228T223633Z__local_fullcap__canary_shard_00`
