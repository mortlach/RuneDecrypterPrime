# Current state

Status: active
Work status: in_progress
Project: rdp_v1

## Short read

`rdp_v1` is the repo-level convergence and release-shaping home.

This project is no longer mainly blocked on finding documents.
It now has a cleaner shape:

- a front-door live pack
- active planning files
- architecture/code-crosscheck files
- one grouped supporting-reference layer
- direct evidence snapshots kept behind the live pack

The main migration-closeout work is now done.
Historical migration/cutover material for this home is now preserved under:
- `planning_old/projects/rdp_v1/`

The main remaining work is now support/reference discipline, not old-path
retirement.

## Verified code-facing anchors in the reviewed bundle

### Landed enough to treat as real
- `src/rune_decrypter_prime/api/specs.py`
  - `CipherSpec`, `KeySpec`, `SolverSpec`
- `src/rune_decrypter_prime/core/problem/spec.py`
  - `ProblemSpec`
- `src/rune_decrypter_prime/scoring/scorer_report.py`
  - `ScorerReport`
- `src/rune_decrypter_prime/api/data_helpers.py`
  - LP helper layer including `load_lp_master_section`
- benchmark/campaign code under:
  - `tools/benchmarks/community/`
  - `tools/benchmarks/solve_proof/`
  - `tools/benchmarks/periodic_sub_trans/no_wli/`

### Real but not cleanly converged yet
- campaign machinery is still largely under `tools/`
- some public planning language is ahead of the concrete code naming
- the repo still carries older path habits outside this normalised home

### Still treat as target-state language here
Not found cleanly in the reviewed bundle:
- a concrete `RunSpec` symbol
- a concrete `SolverReport` symbol

## Main planning need

Use this home as the clean repo-level convergence surface:
- front-door files first
- active plans second
- architecture/code-crosscheck third
- grouped supporting-reference only after that
