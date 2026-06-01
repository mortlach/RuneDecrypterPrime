# No-WLI Fixed-Instance Solver Development Plan

Authoritative spec:

- `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_solver_development_v1_spec_2026-04-14.md`

Status:

- active as of `2026-04-14`
- Workstream 1 complete at `2026-04-15T05:23:15Z`
- Workstream 2 complete at `2026-04-15T05:40:21Z`
- Workstream 3 complete at `2026-04-15T05:47:59Z`
- Workstreams 4-6 complete at `2026-04-15T05:56:24Z`
- candidate 1 retained replay complete at `2026-04-15T06:21:29Z`
- candidate 1 review cleanup complete at `2026-04-15T16:16:30Z`
- candidate 2 core hook started at `2026-04-15T16:16:30Z`
- candidate 2 shadow verification complete at `2026-04-16T03:15:27Z`
- candidate 2 first exact replay probe timed out at `2026-04-16T03:23:05Z`
- candidate 2 exact `611/search7005` replay complete at `2026-04-16T04:49:04Z`
- candidate 2 exact `611/search7005` control complete at `2026-04-16T05:35:15Z`
- candidate 2 exact `1111/search7004` replay complete at `2026-04-16T06:07:43Z`
- candidate 2 replacement Phase-C shadow verification complete at `2026-04-16T14:54:01Z`

Current baseline output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160503Z__fixed_instance_solver_development_v1/`

Current candidate-verification bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`

## Purpose

Take the frozen fixed panel and use it to answer:

- for one fixed ciphertext instance, what changes in the pipeline actually
  improve solving, and where does the good path get lost?

This phase is about improving solving on frozen problems.
It is not about generating more benchmark landscape.

## Frozen benchmark basis

Primary tuning trio:

- `1511`
  - positive control
- `611`
  - middle unsolved case
- `1111`
  - conversion-failure case

Cross-check case:

- `1411`
  - useful, mixed, but caveated

Frozen evidence packs:

- main panel pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `1111` supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
- cross-seed plus `1111` focus-family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

## Goals

1. Build one clean frozen baseline digest for the panel.
2. Explain `1111` more sharply than:
   - late promise fails to convert
3. Explain what a healthier case looks like using `1511`.
4. Use `611` as the main unsolved tuning case.
5. Only after those analyses, identify one or two justified solver-change
   candidates.

## Non-goals

- no new broad panel
- no live seeds
- no stop-rule changes
- no promoted family-quality head
- no new family-quality-vN branch
- no benchmark expansion
- no blended stage35 count as a headline metric
- no drifting definition of `focus family`
- no benchmark widening before one shortlist candidate is chosen deliberately

## Fixed definitions

### Focus family

Use exactly:

- `focus family = family of the top stage35-admitted row in that run`

Keep it separate from:

- dominant mapped stage35 family
- final-best family

### Stage35 count fields

Always keep these separate:

- `archive_seed_row_count`
- `best_stage35_seed_row_count`
- `space_map_stage35_row_count`

Do not collapse them into one generic stage35 count.

### Trust fields

- planning may say `retained trust-related fields`
- once the implementation becomes concrete, use the actual retained field names

## Workstream 1 - panel baseline digest

Status:

- complete
- generated:
  - `panel_baseline_rows.jsonl`
  - `instance_summary_rows.jsonl`
  - `instance_search_matrix.csv`
  - `fixed_instance_solver_baseline_cases.md`

Required outputs:

- `panel_baseline_rows.jsonl`
- `instance_summary_rows.jsonl`
- `instance_search_matrix.csv`
- `fixed_instance_solver_baseline_cases.md`

Each per-run baseline row must include:

- instance id
- source key seed
- search seed
- run type
- best match ratio
- solved / unsolved / stalled
- best stage
- `archive_seed_row_count`
- `best_stage35_seed_row_count`
- `space_map_stage35_row_count`
- retained trust-related fields
- stage35 selected or not
- family summary if available
- caveat flags
- run provenance

## Workstream 2 - `1111` conversion-failure audit

Status:

- complete
- generated:
  - `1111_conversion_compare_rows.csv`
  - `1111_conversion_failure_audit.md`

Minimum comparison set:

- `1111/7002`
- `1111/7003`
- `1111/7005`

Contrast cases:

- `1111/7004`
- `1111/7001`

Required outputs:

- `1111_conversion_compare_rows.csv`
- `1111_conversion_failure_audit.md`

Minimum comparison fields:

- best match ratio
- best stage
- `archive_seed_row_count`
- `best_stage35_seed_row_count`
- `space_map_stage35_row_count`
- focus family
- dominant mapped stage35 family
- final-best family
- retained trust-related fields
- baseline source or lane if available
- key stage35 notes

## Workstream 3 - `1511` positive-control audit

Status:

- complete
- generated:
  - `1511_positive_control_compare_rows.csv`
  - `1511_positive_control_audit.md`

Minimum comparison set:

- `1511/7001`
- `1511/7002`
- `1511/7003`
- `1511/7005`

Required outputs:

- `1511_positive_control_compare_rows.csv`
- `1511_positive_control_audit.md`

## Workstream 4 - `611` middle-case audit

Status:

- complete
- generated:
  - `611_middle_case_compare_rows.csv`
  - `611_middle_case_audit.md`

Required outputs:

- `611_middle_case_compare_rows.csv`
- `611_middle_case_audit.md`

The memo should answer:

- why `611/7004` gets much further than the other runs
- whether `611` is limited by fragile family concentration, weak continuation,
  or inconsistent arrival in the right late region

## Workstream 5 - `1411` caveat note

Status:

- complete
- generated:
  - `1411_caveat_and_use_note.md`

Required output:

- `1411_caveat_and_use_note.md`

It must keep explicit:

- `1411` remains useful
- `1411/7003` solved at stage 3
- archive-side stage35 rows exist
- family-mapped stage35 rows are absent on the `best / space_map` side
- `1411` is a valid context case, not a clean first-line tuning case

## Workstream 6 - controlled solver-change shortlist

This workstream comes only after Workstreams 1-5.

Status:

- complete
- generated:
  - `candidate_solver_change_shortlist.md`

Required output:

- `candidate_solver_change_shortlist.md`

Allowed candidate areas:

- continuation selection policy
- family-aware budget allocation
- baseline-selector choice where already supported
- stage35 admission or prioritisation only if the audits justify it

Not allowed:

- broad tuning sweeps
- benchmark expansion
- speculative mechanisms with no audit basis

## Implementation order

Phase A:

1. Workstream 1
   - status:
     - complete
2. Workstream 2
   - status:
     - complete
3. Workstream 3
   - status:
     - complete
4. Workstream 4
   - status:
     - complete
5. Workstream 5
   - status:
     - complete

Phase B:

6. Workstream 6
   - status:
     - complete

Phase A and Phase B analysis outputs now exist.
Candidate 1 is now a contained retained-negative reference, and candidate 2 is
now closed in both the original Phase-B form and the simple Phase-C-start
replacement form.

## Candidate 1 retained replay

Status:

- complete on retained `611/search7005`
- no live run attached
- not promotable in the current form

Verification bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`

Readout:

- the simple guard-passing accept override does fire
- under `top_score_then_search` with `accept_guard_passing_score_band_eps = 0.001`,
  the selector chooses archive rank `3`
- replay best match is `0.572`
- that is equal to the selected stage-3 baseline row and below the original
  run best `0.585`
- after the no-harm outcome refinement, the retained run-level projection keeps
  the final best at `stage3_full_refine / 0.585`
- `projected_stage35_used_for_final_best = 0`

Use status:

- keep the code opt-in only
- do not attach a live run in the current form

## Candidate 2 core hook

Status:

- started as an opt-in runtime hook
- saved-pool retained shadow verification complete
- exact retained probes now completed on two retained cases
- replacement Phase-C anchor-family shadow verification complete
- not live-ready

Implementation surface:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

Current runtime proxy:

- Phase-B family preservation policy:
  - `reinforce_top_family_v1`
- canary preset:
  - `stage3_phaseb_top_family_reinforce_p9`

Current read:

- this is the minimal candidate2 grounding on existing code surface
- it reinforces the top-ranked Phase-B family instead of reserving diversity
- synthetic Phase-B tests and runtime-contract canaries pass
- shadow bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T031527Z__candidate2_top_family_reinforce_shadow_v1/`
- all four retained probe cases show saved room for top-family reinforcement on
  the saved `phaseC_candidate_pool_rows` surface
- exact candidate `611/search7005` bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T044904Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/`
  - replay best `0.535`
  - `phaseB_family_reservation_applied = 0`
- exact control `611/search7005` bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T053515Z__candidate2_top_family_exact_control_611_search7005_stage3_replay_v1/`
  - same replay best `0.535`
  - the `611` delta is replay drift, not a candidate2 effect
- exact candidate `1111/search7004` bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T060743Z__candidate2_top_family_reinforce_1111_search7004_exact_stage3_replay_v1/`
  - replay best `0.406`
  - `phaseB_family_reservation_applied = 0`
- whole-panel selected-surface bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T064934Z__candidate2_phaseb_selected_surface_v1/`
  - `20/20` retained runs show `32` selected Phase-B rows and `32`
    preserved families
  - engageable retained runs under the current lever: `0`
- current read:
  - the longer-timeout exact replay path works
  - the current `reinforce_top_family_v1` hook is not engaging on the retained
    cases tested so far
  - the shadow/exact mismatch is now explained:
    - the shadow verifier looked at saved `phaseC_candidate_pool_rows`
    - the live hook acts on the already selected Phase-B rows
    - on the tested exact replays that selected surface is `32` families across
      `32` rows, so `reservation_applied` stays `0`
  - the whole-panel selected-surface diagnostic closes this in the current
    frozen panel:
    - the current candidate2 lever is structurally blocked across all `20`
      retained runs
  - replacement Phase-C start-policy read:
    - policy:
      - `anchor_family_reserved_v1`
    - preset:
      - `stage3_phasec_anchor_family_reserved_p9`
    - whole-panel shadow bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T145401Z__candidate2_anchor_family_reserved_shadow_v1/`
    - retained panel read:
      - `19/20` runs have saved Phase-C candidate-pool surface
      - runs with saved anchor-family room: `0`
      - replacement candidate2 shadow live on panel: `0`
      - baseline Phase-C starts already include the available anchor-family rows
        on the frozen panel
  - current candidate2 conclusion:
    - candidate 2 is now closed in both the Phase-B and simple Phase-C-start
      forms

Current candidate3 line:

- selected narrow candidate:
  - `phaseb_topk_anchor_swap_v1`
- reason:
  - candidate 2 is structurally blocked on the retained surfaces it actually
    uses, while the saved Phase-C start surface still shows real anchor-lane
    tension between the retained anchor and the first actual `phaseB_topk`
    start
- implementation surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- whole-panel shadow bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T151927Z__candidate3_phasec_phaseb_topk_anchor_shadow_v1/`
- whole-panel shadow read:
  - `19/20` retained runs can engage the anchor-swap rule
  - `11` engageable runs favor the first actual `phaseB_topk` start
  - `7` engageable runs favor the retained anchor
  - `1` engageable run is equal
- verifier cleanup now landed:
  - stage3-only exact replays now report delta versus the retained Stage-3
    reference instead of comparing only against the artifact-level overall best
  - the one-hour `611/search7004` control attempt is preserved explicitly as
    insufficient:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T152246Z__candidate3_phasec_anchor_swap_exact_control_611_search7004_stage3_replay_v1/attempt_status.json`
- current exact verification:
  - first cleaned matched exact control on `1511/search7004` is complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T163546Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
  - control result:
    - retained Stage-3 reference `0.571`
    - replay best `0.435`
    - delta `-0.136`
  - replay-fidelity audit on that control is complete:
    - latest bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153730Z__candidate3_exact_control_replay_fidelity_1511_search7004_v1/`
    - first unavailable retained surface:
      - none
    - first actual persisted mismatch:
      - `phaseB_downstream_selected_ordered_hashes`
  - rerun exact control with patched replay-surface persistence is also
    complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T015030Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
    - replay-side ordered surfaces now persist:
      - `phaseB_downstream_selected_summaries = 32`
      - `phaseB_topk_saved_summaries = 1`
    - run-level read is unchanged:
      - replay best `0.435`
      - delta versus retained Stage-3 reference `-0.136`
  - saved-surface verifier for the same case is now complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T052238Z__candidate3_phasec_saved_surface_1511_search7004_v1/`
    - stable saved-surface read:
      - candidate3 can engage on the exact saved Phase-C start surface
      - first distinct `phaseB_topk` start is rank `2`
      - saved-surface `phaseB_topk` minus anchor final match is `0.005`
  - saved-surface exact replay helper on the same case is now complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1/`
    - exact saved-surface read:
      - control reproduces retained `0.571`
      - candidate3 lands at `0.569`
      - candidate minus control is `-0.002`
      - control winner stays on retained `phaseB_topk` rank `2`
      - candidate winner shifts to `phaseB_topk` rank `3`
  - seven additional exact saved-surface checks now exist:
    - `611/search7004`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055021Z__candidate3_phasec_saved_surface_exact_611_search7004_v1/`
      - control `0.758`
      - candidate `0.758`
      - candidate minus control `0.000`
    - `611/search7001`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T152806Z__candidate3_phasec_saved_surface_exact_611_search7001_v1/`
      - control `0.381`
      - candidate `0.383`
      - retained Stage-3 reference `0.450`
      - candidate minus control `+0.002`
      - interpretation:
        - small control-relative gain only
        - saved-surface control still misses the retained Stage-3 winner badly,
          so this is not a clean decision gate
    - `1111/search7002`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055755Z__candidate3_phasec_saved_surface_exact_1111_search7002_v1/`
      - control `0.750`
      - candidate `0.754`
      - retained Stage-3 reference `0.752`
      - candidate minus control `+0.004`
    - `1511/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1/`
      - control `0.686`
      - candidate `0.686`
      - retained Stage-3 reference `0.691`
      - candidate minus control `0.000`
      - interpretation:
        - near-stable positive-control lane
        - candidate3 is neutral here
    - `1511/search7002`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7002_v1/`
      - control `0.842`
      - candidate `0.842`
      - retained Stage-3 reference `0.842`
      - candidate minus control `0.000`
      - interpretation:
        - stable positive-control lane
        - candidate3 is neutral here
    - `1511/search7003`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1/`
      - control `0.844`
      - candidate `0.844`
      - retained Stage-3 reference `0.845`
      - candidate minus control `0.000`
      - interpretation:
        - near-stable positive-control lane
        - candidate3 is neutral here
    - `1111/search7001`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T010939Z__candidate3_phasec_saved_surface_exact_1111_search7001_v1/`
      - control `0.420`
      - candidate `0.420`
      - retained Stage-3 reference `0.420`
      - candidate minus control `0.000`
      - interpretation:
        - stable conversion-failure lane
        - candidate3 is neutral here
    - `1111/search7003`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T011123Z__candidate3_phasec_saved_surface_exact_1111_search7003_v1/`
      - control `0.041`
      - candidate `0.041`
      - retained Stage-3 reference `0.323`
      - candidate minus control `0.000`
      - interpretation:
        - drifted conversion-failure lane
        - candidate3 is neutral here, but not on a clean decision gate
    - `1111/search7004`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T011226Z__candidate3_phasec_saved_surface_exact_1111_search7004_v1/`
      - control `0.432`
      - candidate `0.434`
      - retained Stage-3 reference `0.432`
      - candidate minus control `+0.002`
      - interpretation:
        - stable conversion-failure lane
        - candidate3 shows a second small positive on `1111`
    - `1111/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T010749Z__candidate3_phasec_saved_surface_exact_1111_search7005_v1/`
      - control `0.366`
      - candidate `0.366`
      - retained Stage-3 reference `0.416`
      - candidate minus control `0.000`
      - interpretation:
        - drifted conversion-failure lane
        - candidate3 is neutral here
- current rule:
  - do not start a candidate3 live run
  - use stable or near-stable saved-surface exact lanes as the decision gates
  - current exact saved-surface read is:
    - `1511/search7002`: neutral
    - `1511/search7003`: neutral
    - `1511/search7004`: small negative
    - `1511/search7005`: neutral
    - `611/search7004`: neutral
    - `1111/search7001`: neutral
    - `1111/search7002`: positive
    - `1111/search7004`: positive
  - exact-lane matrix summary:
    - `11` total exact cases
    - `8` usable decision gates
    - `3` drifted context lanes
    - usable-gate read:
      - `2` positives
      - `5` neutrals
      - `1` negative
  - `611/search7001` remains useful context only:
    - small positive versus control
    - but not a clean decision gate because control misses the retained winner
  - `1111/search7003` and `1111/search7005` remain useful context only:
    - both are neutral versus control
    - neither is a clean decision gate because the control lane itself drifts
  - exact `1111` family read:
    - stable or near-stable lanes:
      - `7001`: neutral
      - `7002`: small positive
      - `7004`: small positive
    - drifted lanes:
      - `7003`: neutral
      - `7005`: neutral
  - the only usable positive reads are on `1111`
  - the added usable `1511` lanes are neutral rather than positive

## Planned branch location

Use:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/`

Planned documentation files:

- `SPEC.md`
- `EXPERIMENT_PLAN.md`

Implementation files now present:

- `extract_fixed_instance_solver_development_v1.py`
- `tests/tools/test_no_wli_fixed_instance_solver_development_v1.py`

## Output location

Write outputs under:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/<timestamp>__fixed_instance_solver_development_v1/`

Use fixed, hardcoded repo-relative inputs.
Do not auto-discover new runs.

## Decision gates

Gate 1:

- after Workstream 2, can `1111/7002` versus `7003/7005` be explained more
  sharply than "luckier same-family run"?

Gate 2:

- after Workstreams 3 and 4, is there at least one plausible solver-controlled
  difference between `1511` and `611` or `1111`?

Gate 3:

- after Workstream 6, are there one or two narrow, justified candidate changes?

If any gate fails, pause before tuning or benchmark expansion.

## Current next decision

- candidate 1 is still utility-negative in the current form
- the no-harm issue is now contained at the run-outcome layer
- candidate 2 family-aware-budget line is now closed in both current forms:
  - `reinforce_top_family_v1`
  - `anchor_family_reserved_v1`
- candidate 3 is now the active narrow candidate line:
  - `phaseb_topk_anchor_swap_v1`
- immediate next step is to tighten exact Stage-3 replay fidelity, then rerun a
  cleaned control before spending more exact time on the matched candidate pass
- keep the fixed panel frozen and do not start a live run yet
