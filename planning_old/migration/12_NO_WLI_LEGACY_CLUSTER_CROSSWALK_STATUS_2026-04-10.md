# no_WLI legacy cluster crosswalk status - 2026-04-10

Status: done
Work status: retired after preservation
Scope: `planning/old/no_wli_legacy_migration_2026-04-04/`

## Purpose

This note records what was inside the last large old no-WLI cluster and how it
was retired safely.

## Top-level structure

The cluster currently has two substantive top-level subtrees:

| Subtree | File count | Current read |
|---|---:|---|
| `refactor_input_packs/` | 140 | two large frozen baseline/refactor bundles, each with 70 files |
| `review_and_research_packs/` | 329 | now reduced to the two external-review evidence packs |

Retired during this audit:
- empty `working_flat_snapshot/` residue

## Refactor input packs

### `no_wli_planning_refactor_20260404/`

This is a larger frozen planning-refactor pack than the currently promoted
archive copy in:
- `planning/archive/no_wli_planning_refactor_20260404/`

Current state:
- the promoted archive home keeps a curated 14-file source pack
- the old cluster still holds the fuller 70-file frozen pack
- the fuller pack uses extra wrapper directories rather than the flatter layout
  of the promoted archive source pack
- retirement is not safe until we decide whether the promoted archive should:
  - stay curated, or
  - preserve the fuller frozen pack as an evidence snapshot/source pack

### `planning_no_wli_baseline_20260404_clean/`

This appears to be another 70-file frozen baseline pack with the same broad
shape as the refactor pack above.

Current state:
- not yet explicitly crosswalked into the migrated bundle
- likely duplicate-heavy, but not safe to delete until file-level overlap,
  wrapper-path differences, and destination are written down

## Review and research packs

### `no_wli_deep_research_pack_2026-03-21/`

This is small and now fully absorbed, then retired from the old cluster:
- `README.md`
- `capability_ladder_no_wli_periodic_sub_trans_2026-03-21.md`
- `evidence_gaps_no_wli_periodic_sub_trans_2026-03-21.md`
- `method_families_next_capability_jump_2026-03-21.md`
- `tactical_refactor_filter_solve_first_2026-03-21.md`

Those three files are already referenced by:
- `planning/projects/p13_real_ciphertext_campaign/40_supporting_reference/reference_context/35_reference_context/P13_READINESS_CONTEXT_MAP.md`

Current state:
- the whole 5-file pack is preserved through the `p13` readiness-context home
- the old deep-research subpack is now retired

### `no_wli_external_review_pack_2026-03-26/`

This is a medium review/evidence pack.

Current state:
- likely overlaps with already-preserved stage35 and no-WLI archive material
- not yet explicitly mapped into the migrated bundle

### `no_wli_external_review_pack_2026-03-30/`

This is the largest remaining old planning pack in the repo.

Current state:
- contains 305 files
- includes planning logs plus large evidence/run-dir payloads
- not yet explicitly classified as:
  - archive evidence
  - upstream no-WLI reference
  - duplicate residue

## Current judgement

This cluster is no longer a blocker.

It is now retired because:
- the empty residue was removed
- the deep-research subpack was absorbed into the `p13` readiness-context home
- the two fuller frozen refactor-input packs were preserved under:
  - `planning/archive/no_wli_planning_refactor_20260404/95_evidence_snapshots/`
- the two external-review packs were preserved under:
  - `planning/archive/no_wli_external_review_passes_20260326_20260330/95_evidence_snapshots/`
- the old folder itself is gone

## Residual note

The remaining broader cut-over question is now outside this cluster:
- keep `planning/no_wli/` explicit as the one upstream live exception
- keep `planning/working/` limited to a compatibility stub only
