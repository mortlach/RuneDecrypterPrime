# no-WLI Phase-C Conditioned Ordering Long Harvest Plan

Date: 2026-04-26

Status:

- active plan
- minimal bespoke runner only
- not yet integrated into the full planning/review-pack workflow
- intended for one 30-36 hour evidence-harvest block

## Current carried context

The Stage2 selected-family Phase-A checkpoint subtopic is closed as:

- science claim: provisionally supported on fixed `1111/search7001-7005`
- packaging/provenance: clean enough for external review after reconciliation
- live runtime: still blocked
- production/general policy: not claimed

The next branch should move back to a science mechanism question rather than continuing checkpoint timing work.

## Question

Can the mixed candidate3 / Phase-C ordering results be explained by observable saved-surface features, so that future work can use a conditioned ordering rule rather than a global reorder policy?

## Suspicion

The useful Phase-C start ordering is case-dependent.

Some cells may prefer retained/source ordering, some may prefer existing anchor-swap ordering, and some may benefit from different amounts of `phaseB_topk` frontloading, quota, or replacement.

The useful signal is not just final score. The important evidence is whether the policy actually changed the saved surface, changed the winning candidate, or changed a winner source/rank in a way that explains the score movement.

## Main alternative

The apparent case-dependence is mostly noise or replay artefact. A longer saved-surface harvest will not expose stable route/surface features that explain which ordering policy helps.

## Mechanism layer

- ordering
- allocation
- local search / rescue

This is not a selector-checkpoint branch.

## Run shape

Target cases:

- `1111/search7004`
- `611/search7003`
- `1511/search7005`
- `1511/search7003`

Policy set:

- `source_order`
- `phaseb_topk_anchor_swap_v1`
- `phaseb_topk_frontload_all_v1`
- `phaseb_topk_frontload_1_v1`
- `phaseb_topk_frontload_2_v1`
- `phaseb_topk_frontload_4_v1`
- `phaseb_topk_frontload_8_v1`
- `phaseb_topk_quota_1_v1`
- `phaseb_topk_quota_2_v1`
- `phaseb_topk_quota_4_v1`
- `phaseb_topk_quota_8_v1`
- `phaseb_topk_replace_width_1_v1`
- `phaseb_topk_replace_width_2_v1`
- `phaseb_topk_replace_width_4_v1`
- `phaseb_topk_replace_width_8_v1`

Budget:

- hard wallclock cap: `36h`
- cap checked after each completed policy unit
- partial output is valid and should be reviewed if the cap or interruption is hit

## Script

Runner:

`tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_phasec_conditioned_ordering_long_harvest_v1.py`

Launch script:

`planning/projects/no_wli/60_launch_scripts/no_wli_phasec_conditioned_ordering_long_harvest_launch_2026-04-26.ps1`

Pop-out launcher:

`planning/projects/no_wli/60_launch_scripts/no_wli_phasec_conditioned_ordering_long_harvest_open_terminal_2026-04-26.ps1`

Console log:

`planning/projects/no_wli/50_console_and_watch_logs/no_wli_phasec_conditioned_ordering_long_harvest_2026-04-26.log`

Output parent:

`output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/`

Output bundle shape:

`<timestamp>__phasec_conditioned_ordering_long_harvest_v1/`

## Required saved artefacts

The runner writes after every completed policy unit:

- `matrix_run_state.json`
- `matrix_run_events.jsonl`
- `run_config.json`
- `run_summary.json`
- `phasec_conditioned_ordering_long_harvest_case_rows.jsonl`
- `phasec_conditioned_ordering_long_harvest_case_rows.csv`
- `phasec_conditioned_ordering_long_harvest_policy_summary_rows.csv`
- `phasec_conditioned_ordering_long_harvest_family_summary_rows.csv`
- `phasec_conditioned_ordering_long_harvest_summary.json`
- `phasec_conditioned_ordering_long_harvest_recommendation.json`
- `phasec_conditioned_ordering_long_harvest_readout.md`
- per-case `case_manifest.json`
- per-policy `candidate_saved_surface_summary.json`
- per-policy `comparison_summary.json`
- per-policy `surface_diagnostics.json`

## Review question

After the run, review only this:

Did the long harvest produce enough route/surface evidence to design a conditioned Phase-C ordering rule?

Do not review it as a solver-success run first. Solver score is secondary to route/surface interpretation in this branch.

## Advance / hold / close

Advance if:

- completed or partial artefacts are valid and readable
- at least one policy preference difference is explained by saved-surface diagnostics
- the explanation uses fields such as selected-surface change, winner identity change, winner source/rank change, effective applied width, and candidate minus control
- the result points to a possible conditioned rule

Hold if:

- the run saves usable data but not enough cells/policies complete
- policy differences are present but not explainable
- output provenance is incomplete
- timing or interruption prevents confident interpretation

Close if:

- no stable route/surface explanation appears
- policy differences remain tiny/noisy across completed cases
- no conditioned rule direction emerges

## Non-goals

Do not use this branch to:

- tune the Stage2 checkpoint threshold
- reopen live runtime
- promote a global Phase-C ordering policy
- run a broad unconstrained matrix
- mix in Stage-3.5 rescue changes

## After the run

If the output is useful, integrate it properly into the repo planning style after review. That later integration can add a review note, experiment-index update, and possibly a narrower extractor.

Do not do that before the long run unless it is needed to make the run safe.