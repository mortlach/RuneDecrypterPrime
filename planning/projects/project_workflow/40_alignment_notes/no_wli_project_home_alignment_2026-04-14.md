# no_wli project-home alignment - 2026-04-14

Status: active
Work status: done
Project: project_workflow

## What has now been done

`no_wli` has now been promoted into `planning/projects/` as a real active
project home.

It keeps its specialised front-door model:
- `00_CURRENT_STATE.md`
- `01_EXPERIMENT_INDEX.md`
- `02_OPEN_QUESTIONS.md`
- `03_DOCUMENT_MAP.md`
- `04_ACTIVE_RUNBOOK.md`

It also keeps its method-development buckets:
- `10_full_logs/`
- `20_active_plans/`
- `30_analysis_specs/`
- `40_review_summaries/`
- `50_console_and_watch_logs/`
- `60_launch_scripts/`

## Why this is the right model

`no_wli` is not a thin downstream project.
It is the upstream experiment and solver-learning home.

So the right cleanup was:
- move it into `projects/` so the planning root stays tidy
- keep its established experiment-driven reading model
- avoid forcing it into a thinner project shape that would hide the real live
  evidence flow
