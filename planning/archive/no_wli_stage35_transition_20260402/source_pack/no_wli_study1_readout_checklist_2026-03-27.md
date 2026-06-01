# Study 1 Readout Checklist

Purpose:

- evaluate the live `seed211` two-job compare prepared for Study 1
- confirm that the candidate really exercised the new Stage-3 entry policy
- distinguish "policy executed" from "policy helped"

Active control files:

- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
- event log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
- plan:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`

Intended job order:

1. `stage3_preserve_tieband_probe_p9`
2. `stage3_entry_const_local_depth_p9`

Primary hypothesis:

- on `seed211`, the current weak path is partly caused by Stage-3 entry
  compression
- if promoted-family count is large, the legacy fixed-budget Stage-3 entry path
  silently collapses family breadth back toward the narrow entry target
- the constant-local-depth candidate should preserve one row per promoted family
  first, then add one explicit mutation per family, with a cap high enough to
  avoid immediate re-collapse

Policy semantics to verify:

- implementation:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
- candidate preset:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- expected candidate settings:
  - `entry_allocation_policy = "constant_local_depth"`
  - `entry_mutations_per_promoted = 1`
  - `stage3_init_keys_cap = 288`
- expected candidate target math:
  - `stage3_entry_target_before_cap = max(stage3_entry_base_budget, promoted_keys_count * (1 + entry_mutations_per_promoted))`
- expected practical implication on a large promoted pool:
  - if `promoted_keys_count = 144`, target before cap should be `288`
  - with cap `288`, `init3_n` should also become `288`

Completion gate:

- only interpret results after the run-state file shows:
  - `completed_jobs = 2`
  - `remaining_jobs = 0`
  - `stopped_early = 0`

Evidence files to inspect for each completed run:

- run-level summary:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/<run_dir>/instances.json`
- final artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/<run_dir>/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json`
- live handoff manifest:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/<run_dir>/resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed211/manifest.json`
- saved Stage-3 prep bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/<run_dir>/resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed211/stage3_prep.json`
- run config:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/<run_dir>/run_config.json`

How to map the two runs:

- use the event log to confirm job order:
  - job 1 is `stage3_preserve_tieband_probe_p9`
  - job 2 is `stage3_entry_const_local_depth_p9`
- then confirm the preset in each run's `run_config.json`
- do not infer control vs candidate only from directory ordering if any doubt

Readout questions:

1. Did the run complete cleanly?

- confirm both jobs completed with no early stop
- confirm each run emitted:
  - `instances.json`
  - `final_instances/...seed211.json`
  - `resume_handoffs/.../manifest.json`
  - `resume_handoffs/.../stage3_prep.json`

2. Did the candidate actually execute the new policy?

- control should show:
  - `stage3_entry_allocation_policy = "legacy_fixed_budget"`
- candidate should show:
  - `stage3_entry_allocation_policy = "constant_local_depth"`
- candidate should also show:
  - `stage3_entry_mutations_per_promoted_cfg = 1`
  - `stage3_entry_cap = 288`

3. Did the candidate materially widen Stage-3 entry?

- compare control vs candidate in `stage3_prep.json` and the handoff manifest
- required fields:
  - `stage3_promoted_keys_count`
  - `stage3_entry_base_budget`
  - `stage3_entry_target_before_cap`
  - `stage3_entry_cap`
  - `stage3_entry_cap_applied`
  - `init3_n`
- also compare manifest values:
  - `stage2_to_stage3.stage2_promoted_from_topk_count`
  - `stage2_to_stage3.stage3_init3_count`

Positive evidence for Study 1 execution:

- candidate `stage3_entry_target_before_cap` is materially above control
- candidate `init3_n` is materially above control
- candidate `stage2_to_stage3.stage3_init3_count` is materially above control
- candidate widened because of entry policy, not because the upstream promoted
  pool was different by chance

4. Did wider entry help solve quality?

- compare in `instances.json`:
  - `best_stage`
  - `best_match_ratio`
  - `stage3_match_ratio`
- compare in final artifact if available:
  - `phaseB_selected_unique_end_hash`
  - `phaseC_candidate_pool_unique_end_hash`
  - `phaseC_start_keys_used`

Success criteria:

- candidate clearly widens actual Stage-3 entry
- candidate improves either:
  - `stage3_match_ratio`
  - or `best_match_ratio`
- the gain is not explained only by late rescue activity or unrelated drift

Neutral or mixed outcome:

- candidate clearly widens Stage-3 entry
- but `stage3_match_ratio` and `best_match_ratio` stay flat
- interpretation:
  - Study 1 executed correctly
  - but entry width alone was not enough on this seed

Failure criteria:

- candidate does not materially change:
  - `stage3_entry_target_before_cap`
  - `init3_n`
  - or `stage3_init3_count`
- or the candidate silently falls back to legacy behavior
- interpretation:
  - implementation or preset wiring did not actually exercise Study 1

Important interpretation guardrails:

- do not treat a solve-quality miss as an implementation miss if the entry
  telemetry proves that the candidate executed correctly
- do not treat a wider `stage2_promoted_from_topk_count` as a Study 1 win by
  itself; Study 1 is about preserving local depth at Stage-3 entry, not about
  changing Stage-2 promotion
- do not claim broader strategic success from this run alone:
  - this is a single-seed `211` study
  - its best role is testing the upstream reach hypothesis

What this run can and cannot tell us:

- this run can test whether constant-local-depth entry is a real lever on an
  upstream-reach case
- this run cannot settle the downstream-exploitation question for `411`-like
  cases
- if Study 1 executes correctly but stays flat, that strengthens the case for
  moving next to Phase-C start balancing on `411`-like seeds
