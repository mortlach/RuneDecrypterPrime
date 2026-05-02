# Fixed-Instance Solver Development v1 Plan

Question:

- for one fixed ciphertext instance, what changes in the pipeline actually
  improve solving, and where does the good path get lost?

Scope:

- baseline digest for the frozen fixed panel
- `1111` conversion-failure audit
- `1511` positive-control audit
- `611` middle-case audit
- `1411` caveat note
- one or two justified solver-change candidates only after those audits
- first controlled candidate:
  - guard-aware stage35 followup acceptance for coherent late routes

Execution:

- read the three frozen review packs from hardcoded repo-relative paths
- build deterministic panel baseline rows
- keep `archive_seed_row_count`, `best_stage35_seed_row_count`, and
  `space_map_stage35_row_count` separate
- keep `focus family`, dominant mapped stage35 family, and final-best family
  separate
- write the required machine-readable comparison tables and short markdown
  memos
- only after that, write a narrow candidate-change shortlist
- after shortlist review, implement only one opt-in candidate at a time

Current candidate in code:

- selected first candidate:
  - stage35 guard-passing row selection inside the accept gate
- rationale:
  - retained `611/7005` evidence shows the top archive row failed the search
    guard, but a lower preview row still beat both the baseline full score and
    the baseline search score
- implementation surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage35_substitution_solver.py`
- opt-in cfg keys:
  - `accept_guard_passing_selector_mode = "top_score_then_search"`
  - `accept_guard_passing_score_band_eps = 0.001`
- default remains:
  - off
- retained replay verification:
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`
  - case:
    - retained `611/search7005` `score_plus_novelty` baseline row
  - readout:
    - stage35-only replay accept now fires
    - selector lands on archive rank `3`, not the retained preview rank `2`
    - selected stage35 replay best match is `0.572`
    - that equals the selected stage-3 baseline row and is below the original
      run best `0.585`
    - the no-harm outcome refinement now preserves the retained run-level best
      at `stage3_full_refine / 0.585`
    - `projected_stage35_used_for_final_best = 0`
- current conclusion:
  - this candidate is not ready for a live run in the current form
  - the no-harm issue is contained, but there is still no positive utility on
    the retained case
  - keep the code opt-in only as a contained retained-negative reference

Semantic rule:

- stage35 selection telemetry and run-level final-best reporting are separate
- `stage35_selected = 1` does not imply `best_stage = stage35_substitution_only`
- run-level promotion now requires stage35 truth to be known and at least as
  strong as the current best-known outcome

Current next-candidate state:

- move to candidate 2:
  - family-aware budget allocation once a coherent focal family appears
  - first runtime proxy:
    - Phase-B policy `reinforce_top_family_v1`
  - first preset:
    - `stage3_phaseb_top_family_reinforce_p9`
  - do not keep polishing candidate 1 without a specific new selector objective
  - retained shadow verification:
    - bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T031527Z__candidate2_top_family_reinforce_shadow_v1/`
    - read:
      - all four retained probe cases show saved room for top-family
        reinforcement on the saved `phaseC_candidate_pool_rows` surface
      - this was enough to justify exact retained probes, but not enough to
        predict real policy engagement
  - exact retained probes:
    - candidate `611/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T044904Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/`
      - replay best `0.535`
      - `phaseB_family_reservation_applied = 0`
    - matched exact control `611/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T053515Z__candidate2_top_family_exact_control_611_search7005_stage3_replay_v1/`
      - control also lands at `0.535`
      - the `611` delta is replay drift, not a candidate2 effect
    - candidate `1111/search7004`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T060743Z__candidate2_top_family_reinforce_1111_search7004_exact_stage3_replay_v1/`
      - replay best `0.406`
      - `phaseB_family_reservation_applied = 0`
    - whole-panel selected-surface diagnostic:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T064934Z__candidate2_phaseb_selected_surface_v1/`
      - `20/20` retained runs show `32` selected rows and `32` preserved
        families
      - engageable retained runs under the current lever: `0`
  - next required step:
    - stop treating candidate2 as blocked mainly by replay cost
    - treat the shadow/exact mismatch as the main issue:
      - the shadow read looked at saved `phaseC_candidate_pool_rows`
      - the exact hook acts on already selected Phase-B rows
      - on the tested exact cases that surface is `32` families across `32`
        rows, so the current lever cannot engage
    - the cheaper Phase-B selected-surface diagnostic is now done and agrees
      with the exact probes, so the next move is to re-spec or replace the
      candidate2 lever before spending more long exact runs
  - replacement runtime proxy:
    - Phase-C start policy `anchor_family_reserved_v1`
  - replacement preset:
    - `stage3_phasec_anchor_family_reserved_p9`
  - replacement evidence:
    - focused Phase-C tests pass
    - runtime-contract canary passes
    - whole-panel saved-surface shadow bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T145401Z__candidate2_anchor_family_reserved_shadow_v1/`
    - retained panel read:
      - `19/20` runs have saved Phase-C candidate-pool surface
      - runs with saved anchor-family room: `0`
      - replacement candidate2 shadow live on panel: `0`
      - baseline Phase-C starts already include the available anchor-family
        rows on the frozen panel
  - current conclusion:
    - candidate 2 is now closed in both the Phase-B and simple Phase-C-start
      forms
    - do not spend more exact replay time on this candidate line as currently
      specified
    - choose a new narrow candidate instead of extending the blocked
      candidate2 family-aware-budget path

Current candidate3 plan:

- selected narrow line:
  - `phaseb_topk_anchor_swap_v1`
- whole-panel shadow bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T151927Z__candidate3_phasec_phaseb_topk_anchor_shadow_v1/`
- whole-panel shadow read:
  - `19/20` retained runs can engage the anchor-swap rule
  - `11` engageable runs favor the first actual `phaseB_topk` start
  - `7` engageable runs favor the retained anchor
  - `1` engageable run is equal
- exact-verifier correction:
  - stage3-only exact replay summaries now report delta versus the retained
    Stage-3 reference
- exact verification sequence:
  - timed-out one-hour `611/search7004` control attempt is preserved explicitly
    as insufficient:
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
      - control-lane drift starts before the saved top-k and Phase-C start
        surfaces
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
    - scope:
      - stable per-case ordering reference only
      - not a fresh candidate replay
  - saved-surface exact replay helper is now complete for the same case:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1511_7004.py`
    - bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1/`
    - read:
      - saved-surface control reproduces retained `0.571`
      - candidate3 lands at `0.569`
      - candidate minus control is `-0.002`
      - control winner stays on retained `phaseB_topk` rank `2`
      - candidate winner shifts to `phaseB_topk` rank `3`
  - same exact saved-surface check on `611/search7004`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055021Z__candidate3_phasec_saved_surface_exact_611_search7004_v1/`
    - read:
      - control reproduces retained `0.758`
      - candidate3 also lands at `0.758`
      - candidate minus control is `0.000`
  - same exact saved-surface check on `1111/search7002`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055755Z__candidate3_phasec_saved_surface_exact_1111_search7002_v1/`
    - read:
      - control lands at `0.750`
      - candidate3 improves to `0.754`
      - retained Stage-3 reference is `0.752`
      - candidate minus control is `+0.004`
  - same exact saved-surface check on `611/search7001`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T152806Z__candidate3_phasec_saved_surface_exact_611_search7001_v1/`
    - read:
      - control lands at `0.381`
      - candidate3 improves to `0.383`
      - retained Stage-3 reference is `0.450`
      - candidate minus control is `+0.002`
      - saved-surface control still misses the retained winner materially
  - same exact saved-surface check on `1511/search7005`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1/`
    - read:
      - control lands at `0.686`
      - candidate3 also lands at `0.686`
      - retained Stage-3 reference is `0.691`
      - candidate minus control is `0.000`
  - same exact saved-surface check on `1511/search7002`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7002_v1/`
    - read:
      - control lands at `0.842`
      - candidate3 also lands at `0.842`
      - retained Stage-3 reference is `0.842`
      - candidate minus control is `0.000`
  - same exact saved-surface check on `1511/search7003`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1/`
    - read:
      - control lands at `0.844`
      - candidate3 also lands at `0.844`
      - retained Stage-3 reference is `0.845`
      - candidate minus control is `0.000`
  - same exact saved-surface check on `611/search7005`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T014639Z__candidate3_phasec_saved_surface_exact_611_search7005_v1/`
    - read:
      - control lands at `0.585`
      - candidate3 improves to `0.589`
      - retained Stage-3 reference is `0.615`
      - candidate minus control is `+0.004`
      - this is still context only because the control lane itself drifts
- current stop rule:
  - do not treat candidate3 as uniformly good
  - do not attach candidate3 to live runtime yet
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
    - `12` total exact cases
    - `8` usable decision gates
    - `4` drifted context lanes
    - usable-gate read:
      - `2` positives
      - `5` neutrals
      - `1` negative
  - `611/search7001` is context only:
    - small positive versus control
    - but not a clean decision gate because control misses the retained winner
  - `611/search7005` is also context only:
    - small positive versus control
    - but not a clean decision gate because control still misses retained
  - `1111/search7003` and `1111/search7005` are also context only:
    - both are drifted lanes
    - both are neutral
  - candidate3 remains alive, but only narrowly:
    - current evidence is mixed and small-effect
    - it is still a positional reorder probe, not an established solver
      improvement
    - the added usable `1511` lanes are neutral, while the usable positive
      reads remain concentrated on `1111`
    - it now needs review plus control-lane fidelity discipline before any
      live runtime decision

Constraints:

- no CLI arguments
- no latest-bundle discovery
- no live runs
- no runtime or solver tuning before the baseline and audit outputs exist
