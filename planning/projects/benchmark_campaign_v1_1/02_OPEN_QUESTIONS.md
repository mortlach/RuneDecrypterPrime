# Open questions

## B1. What is left after retiring the old `planning/drafts/` benchmark surface?
Current read:
- the old `planning/drafts/` surface is gone
- the absorbed benchmark duplicates are retired
- the non-benchmark leftovers were preserved elsewhere and retired from the old surface

## B2. Which support docs should stay inside this project home?
Likely yes:
- cleanup plan
- refactor plan
- scoring/Torch gates
- setup/preflight

## B3. Which former draft files are now only legacy or archive residue?
Current explicit retired examples:
- old benchmark duplicate docs now owned by this home
- `score_harden_v2.txt`, now preserved in archive
- `v1_core_bugs_bloat_docs_log_2026-02-23.md`, now preserved in `archive/forensic_audit_2026/`

## B4. What should be the boundary with `rdp_v1`?
Keep release-level architecture and repo-level truth under `rdp_v1`.
Keep benchmark execution, campaign rules, and operational benchmark flow here.

## B5. Should this home own a short result-read layer?
Probably yes, once migration closeout is complete.
