# Fixed-Instance Solver Development v1

Authoritative contract:

- `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_solver_development_v1_spec_2026-04-14.md`

This branch is the analysis-first next phase built on the frozen fixed `20`-job
panel.

Frozen inputs:

- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

Primary trio:

- `1511`
- `611`
- `1111`

Cross-check case:

- `1411`

Required outputs:

- `panel_baseline_rows.jsonl`
- `instance_summary_rows.jsonl`
- `instance_search_matrix.csv`
- `fixed_instance_solver_baseline_cases.md`
- `1111_conversion_compare_rows.csv`
- `1111_conversion_failure_audit.md`
- `1511_positive_control_compare_rows.csv`
- `1511_positive_control_audit.md`
- `611_middle_case_compare_rows.csv`
- `611_middle_case_audit.md`
- `1411_caveat_and_use_note.md`
- `candidate_solver_change_shortlist.md`

Selected first candidate:

- `stage35_guard_passing_followup_acceptance_v1`
  - status:
    - implemented in core stage35 code
    - retained replay completed on `611/search7005`
    - no-harm outcome refinement now landed in the stage3 outcome path
    - review cleanup landed:
      - `NaN` `stage35_match` no longer auto-promotes stage35 to final best
      - selector-rescued accepts now report
        `accepted_via_guard_passing_selector`
    - not live-ready in the current form
  - intent:
    - allow the stage35 accept step to choose the best guard-passing archive row
      instead of hard-failing on the single top-score row
  - opt-in cfg keys:
    - `accept_guard_passing_selector_mode`
    - `accept_guard_passing_score_band_eps`
  - current candidate mode:
    - `top_score_then_search`
  - retained replay bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`
  - retained replay read:
    - candidate accept fires in the stage35-only replay
    - selector chooses archive rank `3` inside the score band because it has
      the strongest search score among the guard-passing rows
    - selected stage35 replay best match stays at `0.572`
    - that is equal to the selected stage-3 baseline row and below the original
      run best `0.585`
    - the new run-level no-harm projection keeps the final best at the retained
      `stage3_full_refine` result `0.585`
    - `projected_stage35_used_for_final_best = 0`
  - use status:
    - keep it opt-in only
    - do not attach a live run in the current form
    - if kept, the next refinement question is utility, not no-harm

Outcome semantics:

- stage35 layer:
  - `stage35_selected`
  - `stage35_best_*`
  - stage35 accept / archive telemetry
- run-level layer:
  - `best_stage`
  - `best_match`
  - `final_best_*`
  - `stage35_used_for_final_best`
- these layers are intentionally separate:
  - a stage35 row can be selected and recorded without becoming the final
    run-level best

Current narrow-candidate state:

- `candidate2_family_aware_budget_allocation_v1`
  - reason:
    - candidate 1 is now contained, but still utility-negative on retained
      `611/search7005`
  - first runtime proxy:
    - Phase-B policy `reinforce_top_family_v1`
  - first preset:
    - `stage3_phaseb_top_family_reinforce_p9`
  - implementation status:
    - core hook landed
    - synthetic Phase-B reallocation tests pass
    - runtime-contract canaries pass
    - saved-pool retained shadow verification now complete
    - exact retained replay path now works with a longer timeout
  - shadow verification bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T031527Z__candidate2_top_family_reinforce_shadow_v1/`
  - shadow verification read:
    - all four retained probe cases show saved room for top-family
      reinforcement
    - cases checked:
      - `611/search7005`
      - `1111/search7002`
      - `1111/search7004`
      - `1511/search7002`
    - the saved `phaseC_candidate_pool_rows` surface contains extra anchor-family
      hashes outside the baseline Phase-A selected pool on every checked case
    - this was useful enough to justify exact retained probes, but it did not
      predict actual policy engagement on the exact retained cases tested so far
  - exact retained probes:
    - timed-out first attempt:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T032305Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/`
    - completed longer-timeout candidate replay on `611/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T044904Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/`
      - replay best `0.535` versus retained baseline `0.585`
      - `phaseB_family_reservation_applied = 0`
    - completed longer-timeout exact control on `611/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T053515Z__candidate2_top_family_exact_control_611_search7005_stage3_replay_v1/`
      - control also lands at `0.535`
      - this makes the `611` delta replay drift, not a candidate2 effect
    - completed longer-timeout candidate replay on `1111/search7004`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T060743Z__candidate2_top_family_reinforce_1111_search7004_exact_stage3_replay_v1/`
      - replay best `0.406` versus retained baseline `0.423`
      - `phaseB_family_reservation_applied = 0`
  - current exact read:
    - exact retained replay is now possible with longer runtimes
    - the current `reinforce_top_family_v1` hook has not engaged on the two
      retained cases tested so far
    - the likely reason is surface mismatch rather than replay blockage:
      - the shadow verifier reasoned over saved `phaseC_candidate_pool_rows`
      - the live hook acts on the already selected Phase-B rows
      - on the tested exact replays that selected surface is `32` families
        across `32` rows, so no family reservation can actually fire
    - the whole-panel selected-surface diagnostic now makes this stronger:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T064934Z__candidate2_phaseb_selected_surface_v1/`
      - retained panel read:
        - `20/20` runs have `32` selected Phase-B rows and `32` preserved
          families
        - engageable retained runs under the current lever: `0`
    - do not treat candidate 2 as shadow-supported in a practical sense anymore;
      it is now exact-probed but non-engaging on tested retained cases
  - replacement runtime proxy:
    - Phase-C start policy `anchor_family_reserved_v1`
  - replacement preset:
    - `stage3_phasec_anchor_family_reserved_p9`
  - replacement implementation status:
    - core start-policy branch landed
    - focused Phase-C tests pass
    - runtime-contract canary passes
    - whole-panel saved-surface shadow verification complete
  - replacement shadow bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T145401Z__candidate2_anchor_family_reserved_shadow_v1/`
  - replacement shadow read:
    - `19/20` retained runs have saved Phase-C candidate-pool surface
    - runs with saved anchor-family room: `0`
    - replacement candidate2 shadow live on panel: `0`
    - on the retained panel, the baseline Phase-C starts already include the
      available anchor-family rows:
      - materializable extra anchor-family rows after reservation: `0`
        across all retained runs
    - this closes the simple Phase-C-start re-spec in the same way the
      Phase-B lever was closed:
      - there is no retained room for the new reservation to allocate
  - use status:
    - keep candidate 2 off live runtime in both current forms
    - do not spend more exact replay time on this candidate line as currently
      specified
    - next step is to choose a new narrow candidate rather than extend the
      blocked candidate2 family-aware-budget line

Current candidate3 state:

- selected line:
  - `phaseb_topk_anchor_swap_v1`
- reason:
  - the candidate2 line is closed on its actual retained surfaces, but the
    saved Phase-C start surface still shows real tension between the retained
    anchor lane and the first actual `phaseB_topk` start
- whole-panel shadow bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T151927Z__candidate3_phasec_phaseb_topk_anchor_shadow_v1/`
- whole-panel shadow read:
  - `19/20` retained runs can engage the anchor-swap rule
  - `11` engageable runs favor the first actual `phaseB_topk` start
  - `7` engageable runs favor the retained anchor
  - `1` engageable run is equal
- exact-verifier correction:
  - stage3-only exact replay summaries now compare against the retained
    Stage-3 reference, not only the artifact-level overall best
- exact verification state:
  - one-hour `611/search7004` control attempt is now preserved explicitly as
    insufficient:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T152246Z__candidate3_phasec_anchor_swap_exact_control_611_search7004_stage3_replay_v1/attempt_status.json`
  - first cleaned matched exact control on `1511/search7004` is complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T163546Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
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
    - interpretation:
      - retained ordered Phase-B downstream identities can now be reconstructed
        from persisted `phaseC_candidate_pool_rows` filtered to
        `phaseA_selected`
      - the first actual control-lane drift is therefore earlier than the
        saved top-k and Phase-C start surfaces
  - rerun exact control with patched replay-surface persistence is complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T015030Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
    - replay-side ordered surfaces now persist:
      - `phaseB_downstream_selected_summaries = 32`
      - `phaseB_topk_saved_summaries = 1`
    - run-level read is unchanged:
      - replay best `0.435`
      - delta `-0.136`
  - saved-surface verifier for the same case is now complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T052238Z__candidate3_phasec_saved_surface_1511_search7004_v1/`
    - stable saved-surface read:
      - candidate3 can engage on the exact saved Phase-C start surface
      - first distinct `phaseB_topk` start is rank `2`
      - saved-surface `phaseB_topk` minus anchor final match is `0.005`
    - scope note:
      - this is the stable saved-start reference for candidate3 ordering only
      - it is not a fresh candidate replay and does not bypass the control-lane
        Phase-A/Phase-B drift
  - saved-surface exact replay helper is now complete for the same case:
    - script:
      - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1511_7004.py`
    - bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1/`
    - exact saved-surface read:
      - saved-surface control reproduces the retained Stage-3 reference exactly:
        - retained `0.571`
        - control `0.571`
      - candidate3 on the same exact saved Phase-C starts is slightly worse:
        - candidate `0.569`
        - candidate minus control `-0.002`
      - winner shift:
        - control winner stays on retained `phaseB_topk` rank `2`
        - candidate winner shifts to `phaseB_topk` rank `3`
    - interpretation:
      - the narrower Phase-C-only replay lane is now stable enough to judge
        candidate3 honestly on `1511/search7004`
      - on that exact saved-surface lane, candidate3 is a clean small negative,
        not a replay-fidelity false read
  - the same exact saved-surface helper now has four more retained case checks:
    - middle-case `611/search7004`:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055021Z__candidate3_phasec_saved_surface_exact_611_search7004_v1/`
      - read:
        - saved-surface control reproduces retained `0.758`
        - candidate3 also lands at `0.758`
        - candidate minus control `0.000`
      - interpretation:
        - candidate3 is neutral on this exact saved-surface middle-case lane
    - conversion-failure case `1111/search7002`:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055755Z__candidate3_phasec_saved_surface_exact_1111_search7002_v1/`
      - read:
        - saved-surface control lands at `0.750`
        - candidate3 improves to `0.754`
        - retained Stage-3 reference is `0.752`
        - candidate minus control `+0.004`
        - candidate delta versus retained Stage-3 reference `+0.002`
      - interpretation:
        - candidate3 shows a small positive result on at least one exact
          saved-surface conversion-failure case
    - middle-case `611/search7001`:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T152806Z__candidate3_phasec_saved_surface_exact_611_search7001_v1/`
      - read:
        - saved-surface control lands at `0.381`
        - candidate3 improves to `0.383`
        - retained Stage-3 reference is `0.450`
        - candidate minus control `+0.002`
      - interpretation:
        - small control-relative gain only
        - the saved-surface control lane itself still misses the retained
          Stage-3 winner materially, so this is not a clean decision gate
    - positive-control `1511/search7005`:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1/`
      - read:
        - saved-surface control lands at `0.686`
        - candidate3 also lands at `0.686`
        - retained Stage-3 reference is `0.691`
        - candidate minus control `0.000`
      - interpretation:
        - near-stable positive-control lane
        - candidate3 is neutral here
    - positive-control `1511/search7002`:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7002_v1/`
      - read:
        - saved-surface control lands at `0.842`
        - candidate3 also lands at `0.842`
        - retained Stage-3 reference is `0.842`
        - candidate minus control `0.000`
      - interpretation:
        - stable positive-control lane
        - candidate3 is neutral here
    - positive-control `1511/search7003`:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1/`
      - read:
        - saved-surface control lands at `0.844`
        - candidate3 also lands at `0.844`
        - retained Stage-3 reference is `0.845`
        - candidate minus control `0.000`
      - interpretation:
        - near-stable positive-control lane
        - candidate3 is neutral here
    - middle-case `611/search7005`:
      - bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T014639Z__candidate3_phasec_saved_surface_exact_611_search7005_v1/`
      - read:
        - saved-surface control lands at `0.585`
        - candidate3 improves to `0.589`
        - retained Stage-3 reference is `0.615`
        - candidate minus control `+0.004`
      - interpretation:
        - drifted middle-case lane
        - small control-relative gain only
        - not a clean decision gate because the control lane itself still sits
          well below retained
- current rule:
  - do not treat candidate3 as uniformly good
  - do not start a live candidate3 run from the current exact-lane evidence
  - the saved-surface exact helper is now the correct decision gate only on
    stable or near-stable lanes, not as a globally valid shortcut
  - current exact saved-surface read is case-dependent:
    - `1511/search7002`: neutral
    - `1511/search7003`: neutral
    - `1511/search7004`: small negative
    - `1511/search7005`: neutral
    - `611/search7004`: neutral
    - `1111/search7001`: neutral
    - `1111/search7002`: positive
    - `1111/search7004`: positive
    - drifted context lanes:
      - `611/search7001`: small positive versus control
      - `611/search7005`: small positive versus control
      - `1111/search7003`: neutral
      - `1111/search7005`: neutral
  - exact-lane matrix summary:
    - `12` total exact cases
    - `8` usable decision gates
    - `4` drifted context lanes
    - usable-gate read:
      - `2` positives
      - `5` neutrals
      - `1` negative
  - candidate3 remains alive, but only narrowly:
    - it is still a positional reorder probe, not an established solver
      improvement
    - the added usable `1511` lanes are neutral, while the usable positive
      reads remain concentrated on `1111`
    - it needs case-selection discipline and control-lane fidelity discipline
      before any live use

Non-goals:

- no live runs
- no benchmark expansion
- no stop-rule promotion
- no family-quality-vN branch
- no solver/runtime tuning before the baseline and audits exist
