# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Timing Postmortem Audit Note

Date: 2026-04-25

## Outcome

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T001151Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1/`
- result:
  - `advance`
- review ready:
  - `1`
- live runtime reopen recommended:
  - `0`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_subtopic_synthesis`

## Question

After the restart32 best-init family microbatch passed semantically, what
explains the kept `7004` wallclock inflation relative to its reference exact
replays?

## Read

- control `7003` stayed timing-stable under the same action wiring:
  - family elapsed / reference:
    - `1.007`
  - family Phase-B step2112 elapsed / reference:
    - `0.997`
- kept `7004` was already `keep` early:
  - first keep checkpoint:
    - restart `32`
  - first keep elapsed share:
    - `0.269`
- kept `7004` still slowed broadly:
  - family elapsed / anchor reference:
    - `1.572`
  - family elapsed / latest reference:
    - `1.646`
  - family restart64 elapsed / latest reference:
    - `1.518`
  - family Phase-B step2112 elapsed / latest reference:
    - `2.474`
  - Phase-B step2112 eval rate:
    - family:
      - `13257.4`
    - latest reference:
      - `32803.2`

## What We Learned

- the `7004` slowdown does not read like a late keep decision:
  - the first keep already happens at restart `32`
- it also does not read like generic checkpoint-action overhead:
  - `7003` under the same action wiring stays timing-stable
- instead, the anomaly reads as broad throughput loss across:
  - late Phase A
  - downstream search

So the audit clears the main ambiguity:

- the selector checkpoint contract still looks semantically valid
- the `7004` overrun is an operational timing anomaly, not a gate-logic failure

## Decision

- the selector checkpoint science remains provisionally defensible
- the external-review handoff is not review-ready as packaged because the
  decisive family-microbatch bundle still has an unreconciled provenance
  mismatch
- do not reopen live runtime from this note alone
- if the branch continues experimentally later, it should do so as a new
  explicitly budgeted live-canary decision rather than as unfinished cleanup
