# RDP v1 crosscheck round 2 — 2026-04-09

Status: active
Work status: done
Project: rdp_v1

This note records a second code-facing crosscheck pass for the active `rdp_v1`
home.

## What looks strongly grounded in the reviewed repo bundle

### A. Public/front-door spec surface
Confirmed files:
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/api/__init__.py`

Interpretation:
- front-door spec surface is real
- spec-language convergence is not imaginary

### B. Core problem and scoring surface
Confirmed files:
- `src/rune_decrypter_prime/core/problem/spec.py`
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/scoring/scorer_report_builder.py`

Interpretation:
- problem/report surface exists in code
- report-shape convergence is partly landed

### C. LP-facing API/data helper surface
Confirmed files:
- `src/rune_decrypter_prime/api/data_helpers.py`
- `src/rune_decrypter_prime/data/liber_primus/...`
- `tests/data/test_lp_master_transcript.py`

Interpretation:
- LP-domain capability is real
- completed LP-domain home remains justified

## What still reads as target-state or convergence language

### D. `RunSpec`
Result:
- still not cleanly found as a concrete symbol in the reviewed bundle

Interpretation:
- still treat as target-state/convergence language

### E. `SolverReport`
Result:
- still not cleanly found as a concrete symbol in the reviewed bundle

Interpretation:
- still treat as target-state/convergence language

### F. Campaign ownership outside `tools/`
Result:
- major benchmark/campaign machinery still materially lives under:
  - `tools/benchmarks/community/`
  - `tools/benchmarks/solve_proof/`
  - `tools/benchmarks/periodic_sub_trans/`

Interpretation:
- the v1 concern remains real
- full convergence still not finished

## What this means for the live project home

The `rdp_v1` home is justified as:
- a release-shaping and convergence project
- not a greenfield build
- not fully landed yet

The live pack should therefore keep saying plainly:
- what exists now
- what is support/reference only
- what is still target-state
