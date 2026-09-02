# Add A Scorer Lane

Status: staged V1 draft

Owner paths:
- `src/rdp/core/component_contracts.py`
- `src/rdp/core/config/scoring.py`
- `src/rdp/core/capability_gates.py`
- `src/rdp/scoring/`
- `src/rdp/scoring/scorer_lane_report.py`
- `src/rdp/scoring/scorer_report_builder.py`
- `tests/scoring/`
- `tests/contracts/`

Related coder pages:
- `coder/scoring_pipeline.md`
- `coder/telemetry_and_reports.md`
- `coder/extension_points.md`

## Goal

Add a scorer signal or capability lane with an explicit contract for ranking,
fallback, and reporting.

Scorer lanes are contract-heavy because they can affect solve quality. A lane
must either run, block clearly, or use an explicitly reported fallback.

## Decide The Lane Type

Before writing code, decide the lane role:

| Role | Rank effect | Typical use |
| --- | --- | --- |
| Production scorer lane | `production` | It changes the score used for ranking. |
| Report-only diagnostic | `report_only` | It explains or audits a result without changing ranking. |
| Capability-only lane | `none` | It records availability, assets, or compatibility. |

Do not start from implementation code until this decision is written down.

## Steps

1. Add or reuse a `ScorerLaneName` in `core/component_contracts.py`.
2. Add config fields to `ScoringConfig` only when users need to request or tune
   the lane.
3. Update `ScoringConfig.requested_scorer_lanes()`.
4. Add capability checks for required assets, runtime support, and requested
   fallback behavior.
5. Add the scoring or diagnostic implementation under `scoring/`.
6. Add report sections through `scorer_lane_report.py` or
   `scorer_report_builder.py`.
7. Ensure report-only fields cannot alter ranking, stopping, tie-breaks, or
   candidate selection.
8. Add focused tests.
9. Update docs and allowlists if the lane becomes public or semi-stable.

## Capability Contract

Use the component contract vocabulary:

- `ComponentKind`
- `V1Status`
- `RankEffect`
- `RequestState`
- `EffectiveState`
- `CapabilityStatus`
- `FallbackPolicy`
- `LaneStatus`
- `ScorerCapabilityReport`

Requested production lanes should block when unavailable unless an explicit
reported fallback is part of the contract.

Report-only lanes should not block production ranking unless their request
policy says they are required evidence.

## Reporting Contract

The report should say:

- whether the lane was requested
- whether it was active, blocked, inactive, report-only, or fallback-reported
- whether it had production rank effect
- what asset or runtime issue occurred
- which report section contains lane evidence

For scorer details, use stable keys such as:

- `scorer_lanes`
- `hamming_dictionary`
- `span_hamming`
- `span_lm`
- `word_ngrams`
- `report_builder_diagnostics`

## Tests

At minimum, cover:

- config request detection
- available lane status
- unavailable requested lane behavior
- explicit fallback behavior, if allowed
- report-only lane has no effect on ranking
- report details are JSON-safe
- absolute paths are not exposed in public reports

Use contract tests for lane labels and reserved report detail keys.

## Do Not Do

- Do not make truth data affect production scoring.
- Do not let diagnostics secretly change candidate selection.
- Do not swallow missing required assets.
- Do not add generated assets or local output files to the repo.
