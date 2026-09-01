# RDP V1 contract evidence used by tests

This folder is **test-backed contract evidence**, not the beginner documentation
path.

Several V1 contract tests read files from this exact folder to stop scope drift.
That means these files are part of the tested release boundary. They may look
like docs, CSV, or JSON, but they are also test fixtures and release evidence.

Do not delete, rename, or move this folder as ordinary docs cleanup unless the
corresponding tests are updated in the same change.

## Why this exists

The V1 release needs a small set of explicit drift locks:

- what is included in V1
- what is deliberately not production V1
- which cleanup/deprecation decisions are locked
- which release gates must remain visible
- which evidence rows connect source material to tests

These files make those decisions reviewable and machine-checkable.

## Files used as contract evidence

- `RDP_CORE_DESIGN_PRINCIPLES.md` - single canonical implementation-design principles for the V1 API migration
- `final_source_to_wp_decision_target_test_chain.csv` - source -> WP -> decision -> target -> test chain
- `final_missing_or_new_acceptance_tests.csv` - acceptance-test gap/promotion list from handoff evidence
- `v1_scope_lock.json` - compact V1 included/excluded boundary used by scope-lock tests
- `v1_cleanup_deprecation_ledger.json` - machine-readable cleanup/deprecation ledger
- `d7_acceptance_test_promotion_status.csv` - acceptance-test promotion status rows
- `V1_RELEASE_ACCEPTANCE_GATES.md` - human-readable release acceptance gates used by contract tests
- `V1_AUTHORITY_AND_DECISIONS.md` - final V1 authority hierarchy and human-readable resolved-decision record, including the approved AN4 package-organisation authority
- `AN3_IMPLEMENTATION_SUMMARY.md` - implementation-stage delivery, validation and known qualification exceptions
- `AN3_EXTERNAL_REVIEW_REQUEST.md` - focused external-review entry point and requested disposition
- `v1_resolved_decisions.csv` - machine-readable approved final-integration decisions
- `v1_final_integration_baseline.json` - reviewed repository, branch and source-snapshot baseline
- `V1_ASSET_AND_CI_PROFILES.md` - A1 canonical asset profiles, test markers and workflow tiers
- `../../../assets_manifest_ci_light_v1.json` - exact source-bundled CI-light asset hashes
- `PACK09_DEPENDENCY_REVIEW_A1.md` - A1 retained fixture-closure review and refreshed hashes

## Current staged implementation authority

AN3 is **PASS and closed** at
`f7af2d2d70ae3aab0965b914024a35df2225fb2f`. The two disclosed robustness
REVIEW trials are accepted non-blocking recipe limitations, and beginner
tutorial tiering remains deferred to GitHub issue #4.

AN4-P is **READY and closed**. The approved external planning pack is
`AN4_P_REVIEW_PACK_20260901T151832Z_f7af2d2d.zip`, SHA-256
`12c1c780e533eaaacb971c31f4c1cf1dd1480e62793599171c8121bf6956f72f`.
Its reviewed plan and matrices govern the staged AN4.0-AN4.8 physical package
organisation. The detailed baseline, target, public-surface preservation rules
and move-manifest identity are recorded in `V1_AUTHORITY_AND_DECISIONS.md`.

The planning pack remains external review evidence. It is not copied into this
repository or made another documentation authority tree.

## Human-readable policy/evidence notes

- `D7_CLEANUP_DEPRECATION_POLICY.md`
- `D7_CLOSURE_CHECKLIST.md`
- `D7_IMPLEMENTATION_SUMMARY.md`
- `D7_TUTORIAL_BENCHMARK_POLICY.md`
- `core_runtime_config_contract.md`
- `core_runtime_contract_boundary.md`
- `report_only_diagnostics_contract.md`
- `review_pack_contract.md`
- `scorer_lane_contract.md`
- `stop_reason_contract.md`

## Rules

- Follow `RDP_CORE_DESIGN_PRINCIPLES.md` when implementing or reviewing V1 changes.
- Do not delete source-to-test evidence as cleanup.
- Do not promote experimental/report-only features into V1 production scoring.
- Remove unreleased accidental public/API aliases only under accepted authority,
  after their consumers and relevant tests migrate; do not preserve them through
  compatibility shims.
- Do not add machine-specific absolute paths to public release artefacts.
- If this folder is relocated later, move the tests and docs references in the same commit.
