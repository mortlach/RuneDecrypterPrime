# no-WLI Phase-C Conditioned Ordering Long Harvest Analysis Plan

Date: 2026-04-26

Status:

- active analysis support
- minimal bespoke analysis script
- not yet fully integrated into the wider review-pack workflow
- intended to analyse the current long harvest output

## Source run

Runner:

`tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_phasec_conditioned_ordering_long_harvest_v1.py`

Expected source bundle shape:

`output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/<timestamp>__phasec_conditioned_ordering_long_harvest_v1/`

Known current source bundle:

`output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T174808Z__phasec_conditioned_ordering_long_harvest_v1/`

## Analysis script

`tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/analyse_phasec_conditioned_ordering_long_harvest_v1.py`

## Output bundle

The analysis writes a separate output bundle:

`output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/<timestamp>__phasec_conditioned_ordering_long_harvest_analysis_v1/`

## Question

Did the long harvest produce enough route/surface evidence to design a conditioned Phase-C ordering rule?

## Suspicion

Different cases prefer different Phase-C ordering choices. The useful next rule should be conditioned on saved-surface features rather than promoted as one global policy.

## Main alternative

The policy differences are too small, noisy, or not explainable by saved-surface diagnostics. In that case this branch should hold or close rather than produce a conditioned rule.

## What the analysis must check

The analysis should check:

- source bundle exists
- source row file exists
- source row count matches completed policy units where possible
- required row columns exist
- source state/event/summary/recommendation/readout files exist where expected
- per-case policy preference
- per-policy aggregate signal
- per-family aggregate signal
- route/surface changes
- winner identity/source changes
- whether candidate policies beat reorder controls
- whether observed differences are explainable enough for a conditioned follow-up

## Required source files

Expected in the source harvest bundle:

- `matrix_run_state.json`
- `matrix_run_events.jsonl`
- `run_config.json`
- `phasec_conditioned_ordering_long_harvest_case_rows.csv`
- `phasec_conditioned_ordering_long_harvest_case_rows.jsonl`
- `phasec_conditioned_ordering_long_harvest_summary.json`
- `phasec_conditioned_ordering_long_harvest_recommendation.json`
- `phasec_conditioned_ordering_long_harvest_readout.md`
- `cases/`

The analysis may run on partial output if the source run is still active.

## Analysis outputs

The analysis writes:

- `matrix_run_state.json`
- `matrix_run_events.jsonl`
- `run_config.json`
- `phasec_conditioned_ordering_long_harvest_analysis_integrity.json`
- `phasec_conditioned_ordering_long_harvest_analysis_case_rows.csv`
- `phasec_conditioned_ordering_long_harvest_analysis_case_best_rows.csv`
- `phasec_conditioned_ordering_long_harvest_analysis_policy_signal_rows.csv`
- `phasec_conditioned_ordering_long_harvest_analysis_family_signal_rows.csv`
- `phasec_conditioned_ordering_long_harvest_analysis_condition_signal_rows.csv`
- `phasec_conditioned_ordering_long_harvest_analysis_summary.json`
- `phasec_conditioned_ordering_long_harvest_analysis_recommendation.json`
- `phasec_conditioned_ordering_long_harvest_analysis_readout.md`

## Decision rule

Advance only if:

- source output is readable
- enough rows have completed to compare at least several policies
- at least one policy/family preference is visible
- the preference is tied to route/surface features, not just final score
- no critical provenance or row-format problem blocks interpretation

Hold if:

- the source run is still partial
- source rows are usable but insufficient
- policy differences are present but not explainable
- any required row columns are missing

Close if:

- completed output shows no stable route/surface explanation
- differences remain tiny/noisy across completed cases
- no conditioned-rule direction emerges

## Non-goals

Do not use this analysis to:

- promote a global policy
- reopen live runtime
- tune the Stage2 checkpoint
- claim solver success from score alone
- modify the running harvest output bundle