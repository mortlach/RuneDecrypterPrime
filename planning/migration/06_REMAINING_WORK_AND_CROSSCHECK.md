# Remaining work and crosscheck

This file lists the main work still left to do in the migration, including the
cross-check work still needed.

## A. Global framework work still left

### A1. Decide when the new bundle becomes the canonical truth
Done:
- the final cut-over call is now recorded in
  `13_FINAL_CANONICAL_CUTOVER_DECISION_2026-04-10.md`
- the control layer is now the canonical day-to-day planning surface

### A2. Decide what to do with the remaining old-surface residue
Done for competing old surfaces:
- the old pre-promotion archive wrapper and `planning/v1/` roots are now retired
- the only intentional non-canonical planning surfaces left are:
  - `planning/no_wli/` as an explicit upstream exception
  - `planning/working/` as a compatibility stub
- the remaining legacy residue inside the live `planning/no_wli/` tree is now
  retired under `planning/legacy/no_wli_live_surface_residue_2026-04-14/`

### A3. Decide whether to copy any live no-WLI planning into this bundle
Still not done:
- we deliberately avoided a large-scale live no-WLI copy

Need:
- decide whether the final canonical planning system should:
  - reference the source `planning/no_wli/` tree only
  - or absorb a controlled copy later

### A4. Retire old top-level planning surfaces safely
Done for old competing surfaces:
- `planning/drafts/`, `planning/review/`, `planning/old/`, the old
  pre-promotion archive wrapper, and `planning/v1/` are now retired as
  competing top-level surfaces
- `planning/working/` remains only as a redirect stub
- use `10_OLD_SURFACE_RETIREMENT_MATRIX_2026-04-10.md` for the full audit trail

## B. Cross-checking still left

### B1. Re-check the active homes against the code/tests again
Still worth doing:
- `rdp_v1`
- `benchmark_campaign_v1_1`
- `p13_real_ciphertext_campaign`

Need:
- another pass after any further support-note triage
- especially if support layers move into archive

### B2. Re-check the benchmark scoring/Torch support notes against current tests
We now have a detailed freshness judgement.
Still needed:
- later archive decision if the historical-but-useful notes become clearly superseded

### B3. Re-check `rdp_v1` support notes against current code surfaces
We now have a detailed freshness judgement.
Still needed:
- decide which support notes stay live support
- decide which move to archive later
- keep owner-review scaffolding from silently becoming live truth

### B4. Re-check the p13 real-ciphertext pack against actual code/results
Still needed:
- the first empirical method/run comparison
- the next result note beyond payload parity control
- confirmation of which solve-proof and no-WLI results are the right first upstream anchors

## C. Project-home work still left

### `rdp_v1`
Still left:
- tighten current-state wording further
- decide if some support layers should be moved to archive later
- decide what the cut-over file set is
- cross-check support notes against live code again

### `benchmark_campaign_v1_1`
Still left:
- keep the retired non-benchmark draft residues mapped only through archive/support notes
- decide which support notes stay live support vs later archive-only support
- keep the removed old `planning/drafts/` surface from reappearing as a live habit

### `p13_real_ciphertext_campaign`
Still left:
- write the next real method/run comparison result note
- choose the first empirical method/run comparison
- decide whether any broader p13 notes should become archived project reference
- finish upstream-link/path-hygiene closeout
- continue checking for genuinely relevant old notes without inventing them

## D. What not to do

Do not:
- reopen broad old-surface evacuation work
- pretend all support notes are current truth
- collapse archive/reference/support layers back into the live entry files
