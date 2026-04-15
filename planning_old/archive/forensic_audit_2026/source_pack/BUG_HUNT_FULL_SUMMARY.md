# bug_hunt.txt Full Read Summary

This summary is based on a full read of planning/audit1/bug_hunt.txt and its line-numbered twin planning/audit1/bug_hunt_linenum.txt.

## Preamble and audit rules (BH 0001-0200)
- Evidence-bound audit: no guessing; every claim tied to code behavior and file evidence.
- Focus on solver-blocking risks: sign conventions, dtype boundaries, batch vs scalar equivalence, cross-module assumptions, cache determinism, mutation locality, and telemetry honesty.
- Required finding format: Observed behavior, implicit contract, risk, evidence, stress test, severity.
- Stress tests should be small, adversarial, and isolate one assumption (not full solves).

## Workflow notes and scope mechanics (BH 0201-1600)
- Advises pinning to a commit SHA to avoid drift; otherwise findings are 'as-of' the index state.
- First-pass workflow: inventory files by subsystem, write a contract chain, select 5-10 highest-leverage tests, then deep dive.
- Contains historical references to a repo_links index and dev branch URLs from a prior audit context; those are not authoritative for the current local repo and must be re-verified locally.

## Blocks and chunks (BH 1669+)
- Block 1: WLI contract mismatch across API/config/scoring; leakage across boundaries.
- Block 2: Interruptors + text permutation alignment traps.
- Block 3: Periodic substitution + columnar + interruptors round-trip invariants.
- Block 4: Scoring integrity (dtype honesty, batch vs scalar honesty).
- Chunks referenced: 1, 3, 4, 5, 6, 7B, 8, 10 (these align to BH-S/F/8/10 items in the ledger).

## Additional tests mentioned outside BH item ranges
These appear earlier in bug_hunt.txt (e.g., in inventory/first-pass sections) and are not tied to specific BH items in the ledger. Verify and map them during implementation.

| Test name | Mentioned file(s) | Exists in repo |
| --- | --- | --- |
| test_beam_knobs_effect | tests/solvers/test_beam_knobs_effect.py | false |
| test_determinism_canary | tests/smoke/test_determinism_canary.py | true |
| test_ecdf_ | (not specified) | (unknown) |
| test_keyops_mutation_locality_distribution | (not specified) | (unknown) |
| test_keyops_mutation_preserves_invariants | (not specified) | (unknown) |
| test_lm_cache_isolation | tests/scoring/test_lm_cache_isolation.py | false |
| test_objective_direction_guard | tests/contracts/test_objective_direction_guard.py | false |
| test_permutation_space_interruptors | tests/contracts/test_permutation_space_interruptors.py | false |
| test_runapi_determinism | tests/smoke/test_runapi_determinism.py | true |
| test_score_ranking_parity_numpy_vs_torch | (not specified) | (unknown) |
| test_score_ranking_parity_scalar_vs_batch | (not specified) | (unknown) |
| test_scorer_pct_edges_and_clamps | tests/scoring/test_scorer_pct_edges_and_clamps.py | true |
| test_seed_validation_strict | tests/solvers/test_seed_validation_strict.py | false |
| test_windowing_spans | tests/scoring/test_windowing_spans.py | true |
| test_wli_invariants_string_path | tests/contracts/test_wli_invariants_string_path.py | false |
| test_wli_parity_runeglish | tests/contracts/test_wli_parity_runeglish.py | false |

## File references in bug_hunt.txt
- Total file refs: 110
- Mapped to current repo (after stripping Copy/ or audit_pack_extract/ prefixes): 69
- Missing/unmapped refs: 41
- Examples of missing/unmapped refs (non-authoritative for current repo):
  - com/mortlach/RuneDecrypterPrime/dev/src/rune_decrypter_prime/core/logging_config.py
  - docs/audit/refactor_plan_interruptors_permutation.md
  - docs/audit/refactor_plan_lm_cache.md
  - docs/audit/refactor_plan_scoring.md
  - docs/audit/refactor_plan_solvers.md
  - docs/audit/refactor_plan_wli.md
  - docs/contracts/PERMUTATION.md
  - docs/contracts/SCORING_OBJECTIVE.md
  - docs/contracts/WLI.md
  - docs/contracts/contract_map.md

## Action updates for the implementation plan
- Incorporate the preamble constraints as non-negotiable rules for each chunk (evidence-bound, no guessing).
- Add the unassigned tests above to the test backlog, with decisions on whether to create new files or consolidate.
- Treat any Copy/ or audit_pack_extract paths as historical references; map them to current repo paths or mark as missing and re-verify.