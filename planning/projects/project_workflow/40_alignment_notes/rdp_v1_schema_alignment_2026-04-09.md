# rdp_v1 schema alignment — 2026-04-09

Status: active
Work status: done
Project: project_workflow

## What has now been done

`rdp_v1` has now had a real schema-normalisation pass.

It keeps:
- front-door files
- `10_governance/`
- `20_active_plans/`
- `30_architecture_specs/`
- `95_evidence_snapshots/`

It now groups the older side layers behind:
- `40_supporting_reference/`

Historical cutover/archive material is now expected to sit outside the live
home under:
- `planning_old/projects/rdp_v1/`

## Why this is the right model

This keeps the live reading path clear while still preserving useful secondary
material.

It is a better model for future active-home normalisation than leaving many
equally prominent side folders at top level.
