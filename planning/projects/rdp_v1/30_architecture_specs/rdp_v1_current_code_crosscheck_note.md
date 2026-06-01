# RDP v1 current-code crosscheck note

Status: active
Work status: needs_review
Project: rdp_v1

This note records what was actually confirmed in the reviewed bundle.

## A. Confirmed in code

### A1. Public/front-door spec surface exists
Confirmed files:
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/api/__init__.py`

Confirmed symbols:
- `CipherSpec`
- `KeySpec`
- `SolverSpec`

### A2. Core problem spec exists
Confirmed file:
- `src/rune_decrypter_prime/core/problem/spec.py`

Confirmed symbol:
- `ProblemSpec`

### A3. Scoring report surface exists
Confirmed files:
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/scoring/scorer_report_builder.py`

Confirmed symbol:
- `ScorerReport`

### A4. LP data helper and transcript-facing API exists
Confirmed files:
- `src/rune_decrypter_prime/api/data_helpers.py`
- `tests/data/test_lp_master_transcript.py`

Confirmed behaviour:
- LP master transcript extraction is part of the API/data helper layer
- page- and section-level parity tests exist

### A5. Campaign/benchmark machinery exists
Confirmed paths:
- `tools/benchmarks/community/`
- `tools/benchmarks/solve_proof/`
- `tools/benchmarks/periodic_sub_trans/no_wli/`
- `tests/community/`

## B. Confirmed planning/code mismatch

### B1. `RunSpec` language is ahead of the reviewed code naming
The governance/refactor docs call for one true public run entrypoint:
`RunSpec`.

In the reviewed source/tests bundle, a concrete `RunSpec` symbol was not found.

Current concrete symbols found instead:
- `CipherSpec`
- `KeySpec`
- `SolverSpec`
- `ProblemSpec`

Interpretation:
- `RunSpec` should still be treated as target-state or convergence language here

### B2. `SolverReport` language is ahead of the reviewed code naming
The governance and risk docs speak about `ScorerReport` and `SolverReport`.

A concrete `SolverReport` symbol was not found in the reviewed source/tests
bundle.

Interpretation:
- do not claim this has already landed

### B3. Campaign architecture is still materially tool-owned
The v1 docs say important campaign architecture should not quietly live in
`tools/`.

But the reviewed bundle still contains major benchmark/campaign machinery under:
- `tools/benchmarks/community/`
- `tools/benchmarks/solve_proof/`
- `tools/benchmarks/periodic_sub_trans/`

Interpretation:
- the v1 concern is real
- the convergence work is still needed

## C. Working rule for this project home

State these distinctions plainly:
- landed
- partly landed
- target-state only

Do not compress them into a false “already done” story.
