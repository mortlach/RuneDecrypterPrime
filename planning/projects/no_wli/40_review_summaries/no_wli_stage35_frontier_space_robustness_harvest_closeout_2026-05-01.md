# No-WLI Stage35 Frontier Space Robustness Harvest Closeout

Date: 2026-05-01

## Question

Across held-out Stage 3.5 frontier strata, does deeper bounded local rescue
stabilize useful gains or mostly amplify the shallow mixed signal?

## Mechanism Layer

- local search / rescue

This run deliberately did not test another entry-allocation or simple
accept-pass policy. It used saved frontier rows and a deeper bounded Stage 3.5
continuation to map robustness across strata.

## Runner And Output

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_frontier_space_robustness_harvest_2026-05-01.log`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`

Key files:

- `stage35_frontier_space_robustness_rows.csv`
- `stage35_frontier_space_robustness_stratum_summary_rows.csv`
- `stage35_frontier_space_robustness_summary.json`
- `stage35_frontier_space_robustness_readout.md`
- `stage35_frontier_space_robustness_queue_manifest.json`

## Runtime

Budget:

- intended wallclock: `8h`
- hardcoded wallclock cap: `28800s`
- per-cell cap: `1800s`
- max cells: `48`

Observed:

- status: `completed`
- completed cells: `48 / 48`
- errors: `0`
- elapsed: `12602.918s`
- elapsed hours: `3.501h`
- first cell: `443.854s`
- first-cell projection: `21305.002s`, inside the `28800s` cap

Refreshed timing references:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T234300Z__no_wli_runtime_history_reference_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T234300Z__fixed_runtime_wallclock_reference_v1/`

## Overall Result

Top-level accepted-row read:

- Stage 3.5 selected cells: `32 / 48`
- search-score guard failures: `16 / 48`
- better than shallow among selected: `27 / 32`
- worse than shallow among selected: `3 / 32`
- nonnegative versus selected start among selected: `28 / 32`
- negative versus selected start among selected: `4 / 32`

Accept reasons:

- `accepted`: `26`
- `accepted_via_guard_passing_selector`: `6`
- `search_score_drop_guard_failed`: `16`

## Stratum Result

| stratum | rows | selected | better/worse vs shallow | nonnegative/negative vs selected start | mean selected delta vs shallow | mean selected delta vs start |
|---|---:|---:|---:|---:|---:|---:|
| `calibration_repeat` | `6` | `6` | `6 / 0` | `6 / 0` | `+0.039167` | `+0.148167` |
| `rank1_5_moderate_positive` | `13` | `7` | `6 / 0` | `7 / 0` | `+0.038286` | `+0.054286` |
| `rank6_heldout_positive` | `5` | `3` | `2 / 0` | `3 / 0` | `+0.042667` | `+0.061000` |
| `shallow_negative` | `14` | `10` | `8 / 2` | `7 / 3` | `+0.037100` | `+0.020500` |
| `shallow_neutral` | `10` | `6` | `5 / 1` | `5 / 1` | `+0.037167` | `+0.037167` |

## Negative Rows

Selected rows negative versus selected start:

- `611/search7002 rank 4 4c8d012f01faa5b7`
  - `0.337 -> 0.326`, delta `-0.011`
- `1411/search7002 rank 1 7dba257cb9a2e00e`
  - `0.464 -> 0.453`, delta `-0.011`
- `1111/search7001 rank 6 d94845511e181f7c`
  - `0.041 -> 0.036`, delta `-0.005`
- `1511/search7002 rank 5 0c0afd57d4779633`
  - `0.825 -> 0.823`, delta `-0.002`

Selected rows worse than shallow:

- `1411/search7002 rank 1 7dba257cb9a2e00e`
  - shallow `0.464`, deep `0.453`, delta `-0.011`
- `611/search7002 rank 4 4c8d012f01faa5b7`
  - shallow `0.330`, deep `0.326`, delta `-0.004`
- `1111/search7001 rank 6 d94845511e181f7c`
  - shallow `0.038`, deep `0.036`, delta `-0.002`

## Prediction Comparison

Prediction before launch:

- rank-6 held-out positives mostly remain useful
- shallow negatives and rank `1-5` neutral/positive rows remain mixed enough to
  block a simple policy

Comparison:

- rank-6 held-out positives:
  - supported among accepted rows: `3 / 3` nonnegative versus start and `2 / 2`
    better than shallow, with `2` guard failures
- shallow negatives:
  - mixed as predicted:
    - `10 / 14` selected
    - `7 / 10` nonnegative versus selected start
    - `3 / 10` negative versus selected start
    - `8 / 10` better than shallow
    - `2 / 10` worse than shallow
- rank `1-5` moderate positives:
  - more positive than expected among accepted rows:
    - `7 / 7` nonnegative versus start
    - `6 / 6` better than shallow
  - but still not runtime-ready because `6 / 13` failed the search-score guard
    and the sample was selected posthoc from the shallow harvest
- shallow neutrals:
  - mixed:
    - `5 / 6` nonnegative versus start
    - `1 / 6` negative versus start

Net:

- suspicion mostly held, but the rank `1-5` moderate-positive accepted slice is
  a stronger offline lead than expected
- the main alternative is partially supported only as a lead, not as a policy:
  deeper rescue found broader accepted positives, but not a clean action rule

## Decision

Do not promote a policy directly from this harvest.

Do not launch another broad local-rescue runtime batch immediately.

The useful carried signal is:

- deeper bounded rescue is a real mechanism, not just a shallow one-round
  artifact
- rank-6 is not the only positive slice
- shallow-negative and shallow-neutral strata still admit enough regressions to
  block broad widening
- accepted rank `1-5` moderate positives deserve offline feature/guard
  characterization before any runtime

## Recommended Next

Run an offline acceptance-boundary extractor over this harvest.

The extractor should compare:

- accepted positives
- accepted regressions
- guard-failed rows with high local best values
- accepted rank `1-5` moderate positives
- rank-6 held-out positives

Do not run more runtime until that offline audit answers whether one
predeclared, action-safe feature set can keep the clean accepted positives while
rejecting the known accepted regressions.

## Offline Boundary Audit Result

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_frontier_space_acceptance_boundary_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T235632Z__stage35_frontier_space_acceptance_boundary_audit_v1/`

Coverage:

- rows: `48`
- accepted positives: `28`
- accepted regressions: `4`
- guard failures: `16`
- single-rule scans: `1087`
- two-feature scans: `20292`
- perfect single-rule separators: `0`
- perfect two-feature separators: `0`

Best no-regression sketches:

- single feature:
  - `shallow_resume_minus_selected >= 0.0005`
  - true positives `16`
  - false positives `0`
  - false negatives `12`
- two feature:
  - `stage35_baseline_score >= 0.132556 AND stage35_accept_reason == accepted`
  - true positives `23`
  - false positives `0`
  - false negatives `5`

Interpretation:

- this confirms the overfitting risk
- there is no clean action-safe separator strong enough to justify another
  local-rescue runtime batch
- the best separators are posthoc and either too lossy or too tied to the
  same acceptance surface that produced the signal

Final branch decision:

- close broad local-rescue policy widening for now
- preserve the harvest as mechanism evidence
- move the next work up a level, or require a genuinely held-out validation
  design before any local-rescue runtime resumes
