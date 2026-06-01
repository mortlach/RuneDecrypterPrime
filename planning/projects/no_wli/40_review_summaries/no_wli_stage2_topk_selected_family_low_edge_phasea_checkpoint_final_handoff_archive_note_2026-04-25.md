# Selector Checkpoint Final Handoff Archive Note

Date: 2026-04-25

## Final Gated Verdict

- status:
  - review-ready after provenance reconciliation
- science claim:
  - provisionally supported on fixed `1111/search7001-7005`
- packaging / provenance:
  - clean enough for external review
- live runtime:
  - still blocked
- production / general policy:
  - not claimed

## Carried Contract

- restart:
  - `32`
- checkpoint field:
  - `phaseA_best_init_match`
- threshold:
  - `0.3865`
- `filter` action:
  - fallback plus early stop
- `keep` action:
  - no action

## Why This Is Closed

The prior blocker was not a new empirical contradiction. It was a
provenance/reporting mismatch in the decisive remaining-family microbatch:

- original state/event layer:
  - `hold`
- later summary/recommendation/readout layer:
  - `advance`
- stale row-level value:
  - `7002 action_behaved_as_expected = 0`

That blocker has now been corrected by:

- fixing the shared role contract so `filtered_family` uses filtered-lane logic
- adding focused regression coverage for the original role-label drift
- regenerating the remaining-family derived bundle through the corrected path
- running the hardened provenance audit against the reconciled bundle

## Accepted Audit Gate

Final hardened audit bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T190612Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`

Accepted fields:

- recommendation:
  - `advance`
- row mismatch count:
  - `0`
- recommendation values present:
  - `1`
- missing recommendation layers:
  - none
- state recommendation:
  - `advance`
- final event recommendation:
  - `advance`
- summary-derived recommendation:
  - `advance`
- recommendation JSON:
  - `advance`
- readout:
  - `advance`
- bundle complete:
  - `1`

## Handoff Artefacts

Review pack:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25.zip`

Paired source bundle:

- `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260425T191004Z.zip`

Reconciled family bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T170754Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_reconciled_v1/`

## Boundary Conditions

Do not reopen live runtime from this result alone.

Do not generalize the rule beyond fixed `1111/search7001-7005` from this pack.

Do not promote this as a production solver policy.

The next experiment may start from this carried status:

- science claim:
  - provisionally supported on fixed `1111/search7001-7005`
- packaging / provenance:
  - clean enough for external review
- live runtime:
  - still blocked
- production / general policy:
  - not claimed
