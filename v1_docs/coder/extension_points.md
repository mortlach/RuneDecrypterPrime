# Extension Points

Status: staged V1 draft

Owner paths:
- `src/rdp/ciphers/`
- `src/rdp/keyops/`
- `src/rune_decrypter_prime/solvers/`
- `src/rdp/scoring/`
- `src/rune_decrypter_prime/core/engine/`
- `src/rdp/core/component_contracts.py`
- `src/rdp/core/config/scoring.py`
- `src/rune_decrypter_prime/api/wrappers/`
- `tests/`

Related how-to pages:
- [Add A Cipher](../howto/add_cipher.md)
- [Add A Solver](../howto/add_solver.md)
- [Add A Scorer Lane](../howto/add_scorer_lane.md)
- [Add A Tutorial](../development/adding_a_tutorial.md)

Related tests:
- `tests/docs/test_v1_coder_docs_contract.py`

Stability:
- Semi-stable contributor surface.

## Purpose

This page lists where contributors can extend RDP V1 and how stable each
extension point is today.

It is intentionally practical: some extension points are registry based, while
others still require explicit enum and table updates.

## Extension Matrix

| Extension | Main owner path | Current mechanism | Stability | Start here |
| --- | --- | --- | --- | --- |
| Cipher | `src/rdp/ciphers/` | Exact runtime registry for engine ciphers; `api.experimental` for typed two-input maps/lookups | Semi-stable | [Add A Cipher](../howto/add_cipher.md) |
| KeyOps family | `src/rdp/keyops/` | keyops registry and capability objects | Internal to semi-stable | `coder/key_pipeline.md` |
| Solver | `src/rune_decrypter_prime/solvers/` | `SolverBase` plus explicit `SolverName` and `_SOLVER_TABLE` registration | Internal to semi-stable | [Add A Solver](../howto/add_solver.md) |
| Scorer runtime | `src/rdp/scoring/` | `BaseScorer`, scorer builders, `ScoringConfig.impl` | Internal | `coder/scoring_pipeline.md` |
| Scorer lane | `src/rdp/core/component_contracts.py` and `src/rdp/core/config/scoring.py` | lane enum, request detection, capability/report sections | Semi-stable contract area | [Add A Scorer Lane](../howto/add_scorer_lane.md) |
| Report/artifact | `src/rune_decrypter_prime/api/` | dataclass reports, artifact agreement, manifest rows | Public V1 for known API surfaces | `coder/telemetry_and_reports.md` |
| Tutorial | `tutorials/v1/` | tutorial file, runner entry, metadata alignment | Public docs evidence | `development/adding_a_tutorial.md` |

## General Rules

Every extension should state:

- the owner module
- whether it is public, semi-stable, internal, experimental, or report-only
- whether it affects ranking
- whether it affects stopping
- whether it affects tie-breaks
- whether it affects candidate selection
- what report or telemetry evidence it emits
- what tests prove the contract

Do not add a new component by only making a class importable. Wire it through
the same config, registry, report, docs, and tests that users will rely on.

## Public API Rule

Only promote a new helper to public API when it is meant to be supported.

If the extension is public or semi-stable, update:

- `v1_docs/coder/public_api.md`
- `v1_docs/reference/public_api_allowlist.md`
- `tests/docs/test_v1_coder_docs_contract.py`

If it is internal, keep it documented in the relevant coder page instead of the
public allowlist.

## Contract Rule

Diagnostic or report-only signals must not silently affect production scoring.

If a signal affects ranking, stopping, tie-breaks, or candidate selection, name
that behavior in the scorer or solver docs and cover it with focused tests.

If a signal is report-only, make that visible in:

- `SolverReport`
- `ScorerReport`
- scorer lane reports
- display summaries when relevant

## Minimal Review Checklist

Before asking for review:

1. Add or update the smallest useful unit test.
2. Add a contract test when the behavior crosses API, report, artifact, or docs
   boundaries.
3. Update the relevant coder page.
4. Update a how-to page if a contributor would otherwise copy stale steps.
5. Run focused tests first, then broaden only as risk requires.

Generated logs, caches, benchmark results, and local output files do not belong
in the docs tree or release repo.
