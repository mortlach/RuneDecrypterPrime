# RDP V1 traceability data

This folder is the repo-local copy of the final post-crosschecked V1 handoff evidence needed by D0 tests.

Keep this small and data-only.  Runtime tests must not depend on local review ZIP paths.

Files:

- `final_source_to_wp_decision_target_test_chain.csv` — repaired source -> WP -> decision -> target -> test chain.
- `final_missing_or_new_acceptance_tests.csv` — acceptance tests that still need to be added/promoted.
- `v1_scope_lock.json` — compact V1 included/excluded boundary used by scope-lock tests.
