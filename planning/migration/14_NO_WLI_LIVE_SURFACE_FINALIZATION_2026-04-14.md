# No-WLI live-surface finalization - 2026-04-14

This note records the final cleanup pass on the live `planning/no_wli/` tree
after the earlier planning refactor.

## What was already true before this pass

- `planning/` was already the canonical repo-wide planning system.
- `planning/no_wli/` was already the explicit upstream live exception.
- `planning/working/` was already reduced to a compatibility stub.
- the active no-WLI navigation layer was already centered on:
  - `00_CURRENT_STATE.md`
  - `01_EXPERIMENT_INDEX.md`
  - `02_OPEN_QUESTIONS.md`
  - `03_DOCUMENT_MAP.md`
  - `04_ACTIVE_RUNBOOK.md`

## What this investigation checked

### 1. Where the recent fixed-panel updates landed

The recent `v71`, `v72a`, `v72b`, and `v73` updates landed in the active
no-WLI planning surface, not in old planning homes.

The current run-state and completion wording now lives in:
- `planning/no_wli/00_CURRENT_STATE.md`
- `planning/no_wli/01_EXPERIMENT_INDEX.md`
- `planning/no_wli/04_ACTIVE_RUNBOOK.md`
- `planning/no_wli/10_full_logs/no_wli_science_run_log_2026-03-26.md`
- `planning/no_wli/20_active_plans/no_wli_fixed_instance_mode_infrastructure_plan_2026-04-08.md`

### 2. What legacy residue was still left in the live tree

The no-WLI tree was already mostly in the new structure, but it still exposed:
- `planning/no_wli/90_legacy_index/`
- `planning/no_wli/30_analysis_specs/new 1.txtno_wli_seed_family_triage_shadow_v1_spec_2026-04-08.md`
- `planning/no_wli/30_analysis_specs/no_wli_late_family_quality_v2_spec_2026.md`
- `planning/no_wli/30_analysis_specs/next_steps_april_4_2026.txt`

Those items were provenance or draft residue, not live planning.

## Action taken

That residue is now preserved under:
- `planning/legacy/no_wli_live_surface_residue_2026-04-14/`

The live `planning/no_wli/` surface is now formally:
- top-level `00-04`
- `10_full_logs/`
- `20_active_plans/`
- `30_analysis_specs/`
- `40_review_summaries/`
- `50_console_and_watch_logs/`
- `60_launch_scripts/`

## Working rule going forward

Use the live no-WLI tree only for current planning.

Specifically:
1. start from `planning/no_wli/00_CURRENT_STATE.md`
2. treat only the curated `00-04` layer plus `10/20/30/40/50/60` as live
3. treat `planning/legacy/no_wli_live_surface_residue_2026-04-14/` as
   reference-only provenance
4. treat frozen external-review packs under
   `planning/no_wli/40_review_summaries/` as evidence snapshots, not live
   planning entry points

## Practical conclusion

The refactor is now structurally complete for day-to-day no-WLI planning.

The remaining open decision is only strategic:
- whether `planning/no_wli/` should stay as an explicit upstream exception, or
- whether part of it should later be absorbed into the canonical project-home
  bundle
