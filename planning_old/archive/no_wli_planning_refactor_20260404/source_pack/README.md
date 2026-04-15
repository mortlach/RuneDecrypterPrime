# No-WLI planning folder refactor

This folder is a navigation-first refactor of the current `planning/working`
material.

It keeps the **full evidence logs** intact, but adds a smaller top layer so the
current state, next run, open questions, and document map can be read without
scrolling through the full chronology first.

## Start here

1. `00_CURRENT_STATE.md`
2. `01_EXPERIMENT_INDEX.md`
3. `02_OPEN_QUESTIONS.md`
4. `03_DOCUMENT_MAP.md`
5. `04_ACTIVE_RUNBOOK.md`

## Folder layout

- `10_full_logs/`
  - append-only evidence logs and integrity notes
- `20_active_plans/`
  - implementation plans and active study plans
- `30_analysis_specs/`
  - data-contract and classifier/spec documents
- `40_review_summaries/`
  - one-off comparison notes and review summaries
- `50_console_and_watch_logs/`
  - saved watcher/console logs
- `60_launch_scripts/`
  - one-off PowerShell launch/watch scripts
- `90_legacy_index/`
  - preserved older index docs

## Working rules for this refactor

- Do not delete the full logs; they remain the evidence trail.
- Keep the top-level files short and actively maintained.
- Add new experiments to `01_EXPERIMENT_INDEX.md` and only then expand the
  full science log.
- Keep “what is currently true” in `00_CURRENT_STATE.md`, not buried inside the
  chronology.
- Keep unresolved items in `02_OPEN_QUESTIONS.md` and prune closed ones.

## Current headline state

- The bounded `score_plus_novelty + beam_width_1` lane is a real hard-case
  mechanism proof on `p9/c3 seed411`, but is **not** broad promotion yet.
- `space_map_v1` is now broad enough to be useful from `stage2_promoted`
  through `stage35_archive`, but Stage 3 prep ancestry is still partly
  scaffolding.
- The next highest-value missing evidence is a single fresh mapped hard-seed
  run on `p9/c3 seed611`.
- `score_stop_shadow_v2` remains offline-only analysis and should stay small
  until the first tiny panel readout is inspected.
