# RDP V1 release contracts and evidence

Status: Internal, test-backed V1 release material.

This directory is not part of the normal learning or API-reference route. Most
RDP users do not need it. It preserves the contracts, machine-readable fixtures,
release evidence and historical checkpoints used to keep the V1 boundary
reviewable and testable.

Some Markdown, CSV and JSON files here are consumed directly by tests and
release tools. Do not delete, rename, move or casually rewrite them as ordinary
documentation cleanup.

## Classification

### Active V1 contracts

These describe current V1 behaviour or authority and must remain aligned with
the implementation:

- [`RDP_CORE_DESIGN_PRINCIPLES.md`](RDP_CORE_DESIGN_PRINCIPLES.md) — canonical implementation-design principles.
- [`V1_AUTHORITY_AND_DECISIONS.md`](V1_AUTHORITY_AND_DECISIONS.md) — authority hierarchy and resolved decisions; its named AN3/AN4 sections remain historical snapshots.
- [`V1_RELEASE_ACCEPTANCE_GATES.md`](V1_RELEASE_ACCEPTANCE_GATES.md) — current release gates.
- [`V1_ASSET_AND_CI_PROFILES.md`](V1_ASSET_AND_CI_PROFILES.md) — asset profiles, test markers and CI tiers.
- [`public_api_allowlist.md`](public_api_allowlist.md) — exhaustive current public API surface.
- [`v1_scope_lock.json`](v1_scope_lock.json) — machine-readable included/excluded V1 boundary.
- [`v1_resolved_decisions.csv`](v1_resolved_decisions.csv) — machine-readable resolved decisions.
- [`v1_cleanup_deprecation_ledger.json`](v1_cleanup_deprecation_ledger.json) — current cleanup/deprecation dispositions.
- [`A4_STATE_REPORTING_REPRODUCIBILITY.md`](A4_STATE_REPORTING_REPRODUCIBILITY.md) — run-status, reporting and reproducibility contract.
- [`A5_PACKAGE_ASSET_PROVENANCE.md`](A5_PACKAGE_ASSET_PROVENANCE.md) — package, asset and provenance boundary.
- [`core_runtime_config_contract.md`](core_runtime_config_contract.md) — typed core-runtime configuration boundary.
- [`d3_numpy_strict_requested_lanes.md`](d3_numpy_strict_requested_lanes.md) — strict NumPy requested-lane behaviour.
- [`D5_REPORT_AND_ARTIFACT_AGREEMENT.md`](D5_REPORT_AND_ARTIFACT_AGREEMENT.md) — run-report and artifact agreement.
- [`report_only_diagnostics_contract.md`](report_only_diagnostics_contract.md) — score-neutral diagnostics.
- [`review_pack_contract.md`](review_pack_contract.md) — lightweight V1 review-pack boundary.
- [`scorer_lane_contract.md`](scorer_lane_contract.md) — scorer capability and lane reporting.
- [`stop_reason_contract.md`](stop_reason_contract.md) — stop-reason/status compatibility.
- [`WP7_TWO_PERIOD_CRIBS.md`](WP7_TWO_PERIOD_CRIBS.md) — two-period crib-solver contract.

The related [`../v1_large_lm_assets.md`](../v1_large_lm_assets.md) is the active
large-language-model asset contract.

### Release evidence and test fixtures

These are retained inputs or records. Some are directly consumed by tests or
tools; they are evidence, not general documentation:

- [`A5_PROVENANCE_REVIEW_TEMPLATE.csv`](A5_PROVENANCE_REVIEW_TEMPLATE.csv) — provenance review evidence.
- [`d7_acceptance_test_promotion_status.csv`](d7_acceptance_test_promotion_status.csv) — D7 acceptance-promotion record.
- [`D7_CLEANUP_DEPRECATION_POLICY.md`](D7_CLEANUP_DEPRECATION_POLICY.md) — retained D7 cleanup-policy evidence supporting the ledger.
- [`D7_TUTORIAL_BENCHMARK_POLICY.md`](D7_TUTORIAL_BENCHMARK_POLICY.md) — retained tutorial truth/benchmark policy evidence.
- [`D7_TUTORIAL_OUTPUT_FRAMEWORK.md`](D7_TUTORIAL_OUTPUT_FRAMEWORK.md) — retained evidence for tutorial output contracts now owned by source and tests.
- [`final_missing_or_new_acceptance_tests.csv`](final_missing_or_new_acceptance_tests.csv) — acceptance-test gap/promotion evidence.
- [`final_source_to_wp_decision_target_test_chain.csv`](final_source_to_wp_decision_target_test_chain.csv) — source-to-test traceability evidence.
- [`PACK09_DEPENDENCY_REVIEW_A1.md`](PACK09_DEPENDENCY_REVIEW_A1.md) — retained fixture-closure review.
- [`two_period_fixture_manifest.json`](two_period_fixture_manifest.json) — hash-checked Pack 09 dependency fixture used by tests and tooling.

### Historical checkpoints

These accurately describe named implementation or review stages. Their old
paths, counts, commits and outcomes are historical facts, not current API
claims:

- [`AN3_IMPLEMENTATION_SUMMARY.md`](AN3_IMPLEMENTATION_SUMMARY.md)
- [`core_runtime_contract_boundary.md`](core_runtime_contract_boundary.md) — D3 freeze baseline.
- [`d3_stage_overlays/README.md`](d3_stage_overlays/README.md)
- [`d3_stage_overlays/d3_1_2_capability_gate_overlay.md`](d3_stage_overlays/d3_1_2_capability_gate_overlay.md)
- [`d3_stage_overlays/d3_3_scorer_lane_report_overlay.md`](d3_stage_overlays/d3_3_scorer_lane_report_overlay.md)
- [`d3_stage_overlays/d3_4_numpy_builder_wiring_overlay.md`](d3_stage_overlays/d3_4_numpy_builder_wiring_overlay.md)
- [`d3_stage_overlays/d3_5_report_only_neutrality_overlay.md`](d3_stage_overlays/d3_5_report_only_neutrality_overlay.md)
- [`d3_stage_overlays/d3_6_solver_report_scorer_lanes_overlay.md`](d3_stage_overlays/d3_6_solver_report_scorer_lanes_overlay.md)
- [`d3_stage_overlays/d3_7_targeted_contract_sweep_overlay.md`](d3_stage_overlays/d3_7_targeted_contract_sweep_overlay.md)
- [`d4_contract_closure.md`](d4_contract_closure.md)
- [`D5_CI_AND_CLOSEOUT.md`](D5_CI_AND_CLOSEOUT.md)
- [`D7_FINAL_REVIEW_READY.md`](D7_FINAL_REVIEW_READY.md)
- [`D7_FINAL_SUMMARY.md`](D7_FINAL_SUMMARY.md)
- [`D7_IMPLEMENTATION_SUMMARY.md`](D7_IMPLEMENTATION_SUMMARY.md)
- [`D7_TUTORIAL_BENCHMARK_MATCH_RATIO_ADDENDUM.md`](D7_TUTORIAL_BENCHMARK_MATCH_RATIO_ADDENDUM.md) — superseded by source/tests.
- [`D7_TUTORIAL_INTEGRATION_PASS.md`](D7_TUTORIAL_INTEGRATION_PASS.md)
- [`v1_final_integration_baseline.json`](v1_final_integration_baseline.json) — reviewed branch/snapshot baseline.

### Development and review meta

These describe review or closeout process rather than current public contracts.
They remain because contract tests and retained evidence reference them:

- [`D7_CLOSURE_CHECKLIST.md`](D7_CLOSURE_CHECKLIST.md)
- [`D7_REVIEW_REQUEST.md`](D7_REVIEW_REQUEST.md)

## Current public API snapshot

[`public_api_allowlist.md`](public_api_allowlist.md) contains the current 145-path
contract. The root namespace has 34 exports, including `score`, `score_many`,
`RuneInput`, `RuneInputFormat`, `api.liber_primus.source`, and
`api.liber_primus.load_plaintext` for known solved plaintext references.

The accepted historical 141-path / 32-root-export AN4 checkpoint remains in
the historical evidence and must not be rewritten as though it described the
current surface.

The current canonical CRLF SHA-256 of the allowlist is
`0c43a2f019a39104785490f5230c8aecd39f927282eb38fbf4028f2e27dea3e8`.

## Maintenance rules

- Use the active contracts above when reviewing V1 changes.
- Preserve test-consumed source-to-test and machine-readable evidence.
- Requested production capabilities must run, block clearly or use an explicit reported fallback.
- Report-only diagnostics must not affect ranking.
- Truth/reference data must not silently affect production scoring or selection.
- Keep machine-specific paths, generated output and large assets out of this tree.
- If this directory is reorganised after V1, update every test, tool and document consumer in the same reviewed change.
