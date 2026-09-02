# Scoring Pipeline

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/core/config/scoring.py`
- `src/rune_decrypter_prime/scoring/`
- `src/rdp/core/component_contracts.py`
- `src/rdp/core/capability_gates.py`

Related tests:
- `tests/scoring/`
- `tests/core/`
- `tests/contracts/`
- `tests/torch/`

Stability:
- Public V1 surface for reports
- Internal/contributor surface for scorer runtime internals

## Purpose

The scoring layer ranks candidate plaintext and explains scoring configuration.
It is one of the highest-risk areas for silent drift, so every signal must say
whether it affects ranking or is diagnostic/report-only.

## What This Layer Owns

- objective parsing and normalisation
- production scorer runtime
- scorer reports
- scorer lane capability reports
- optional hamming/span/ngram components
- telemetry derived from scoring
- clear fallback/block/report-only status

## What This Layer Must Not Own

- key search strategy
- cipher transformation
- hidden truth/oracle steering
- silent fallback for requested production lanes
- report-only signal effects on ranking, stopping, tie-breaks, or candidate
  selection

## Main Objects

| Object | Owner path | Role |
| --- | --- | --- |
| `ScoringConfig` | `src/rune_decrypter_prime/core/config/scoring.py` | Canonical runtime scoring configuration. |
| `ObjectiveSpec` | `src/rdp/core/types.py` | Typed objective family/stat/window description. |
| `ScorerReport` | `src/rune_decrypter_prime/scoring/scorer_report.py` | Public scoring evidence surface. |
| `build_scorer_report` | `src/rune_decrypter_prime/scoring/scorer_report_builder.py` | Builds scorer report details from runtime observations. |
| `build_scorer_lane_report` | `src/rune_decrypter_prime/scoring/scorer_lane_report.py` | Reports requested/effective scorer lane status. |
| scorer runtimes | `src/rune_decrypter_prime/scoring/` | Implement ranking and optional component integration. |

## How It Fits Into A Run

```text
typed ScoringConfig on RunSpec
  -> scorer runtime
  -> DecryptionProblem scores candidate plaintext
  -> solver ranks candidates
  -> scorer report / lane report explains scoring
```

## Signal Effect Table

| Signal kind | May affect ranking | May affect stopping | May affect tie-breaks | May affect candidate selection | Notes |
| --- | --- | --- | --- | --- | --- |
| Production objective score | Yes | Yes, through solver stop policy | Yes, if solver uses score order | Yes, through solver search | Must be explicit in objective config. |
| Required production lane | Yes | Yes, if part of objective | Yes | Yes | Requested lane must run or block clearly. |
| Report-only lane | No | No | No | No | May explain a run only. |
| Diagnostics/details | No | No | No | No | Must not steer production ranking. |
| Truth/oracle data | No, unless explicitly test/tutorial-only and reported | Only when explicitly reported as oracle/test path | No hidden effect | No hidden effect | Must be visible in reports. |

## Contracts And Invariants

- Requested production scorer lanes must run or block clearly.
- Report-only diagnostics must not affect ranking.
- Scorer reports must be JSON-safe.
- Absolute local paths must not leak into public report payloads.
- Scorer-lane reports must label request state, effective state, rank effect,
  fallback policy, and report section.

## Determinism Notes

- Same inputs, scorer config, assets, and backend should produce stable scores
  within the documented backend tolerance.
- Optional backends must be explicit about availability and fallback.
- Cache cleanup is coordinated by the engine after runs where supported.
- Asset/version status should be visible when it affects scoring capability.

## Report And Telemetry Outputs

Scoring can contribute:

- objective string
- objective spec
- score and raw score
- metrics
- telemetry
- scorer lane status
- hamming/span/ngram detail sections
- report-builder diagnostics

Report-only sections explain but do not rank.

## Extension Checklist

1. Decide whether the new signal is production or report-only.
2. Add config fields and normalisation.
3. Add runtime implementation.
4. Add scorer report/lane report visibility.
5. Add tests proving rank effect or report-only neutrality.
6. Add no-silent-fallback tests for requested production lanes.
7. Update docs and public API allowlist only for public surfaces.

## What Not To Rely On

- Private scorer runtime caches.
- Diagnostic detail keys as ranking inputs.
- Optional backend availability without explicit status.
- Experimental ngram/hamming paths as V1 production unless promoted by policy.
