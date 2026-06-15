# RDP V1 release-contract data

This folder is the repo-local copy of the final post-crosschecked V1 handoff evidence and release-contract guardrails used by the V1 contract tests.

Keep this folder small, reviewable, and repo-relative. Runtime tests must not depend on local review ZIP paths or machine-specific absolute paths.

## D0/D1 release authority

- `final_source_to_wp_decision_target_test_chain.csv` — repaired source -> WP -> decision -> target -> test chain.
- `final_missing_or_new_acceptance_tests.csv` — original acceptance-test gap/promotion list from the handoff evidence.
- `v1_scope_lock.json` — compact V1 included/excluded boundary used by scope-lock tests.

## D7 cleanup guardrails

- `D7_CLEANUP_DEPRECATION_POLICY.md` — human-readable cleanup/deprecation policy.
- `v1_cleanup_deprecation_ledger.json` — machine-readable ledger for retained, deprecated, future-removal, and removed items.
- `d7_acceptance_test_promotion_status.csv` — current D7 status for acceptance-test rows promoted from the original gap list.
- `D7_CLOSURE_CHECKLIST.md` — final closure checklist and required validation gates.

## Rules

- Do not delete source-to-test evidence as cleanup.
- Do not promote experimental/report-only features into V1 production scoring.
- Do not remove public/API compatibility aliases without updating the cleanup ledger and the relevant tests.
- Do not add machine-specific absolute paths to public release artifacts.
