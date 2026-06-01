# Schema normalisation pass — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

## What changed

This pass did not try to rewrite the whole project.

It did three focused things:

1. kept the front-door files intact
2. kept the main contract/plan/validation layers intact
3. collapsed the cluttered secondary layers behind:
   - `40_supporting_reference/`
   - `90_archive_links/`

## Why this matters

Before this pass, `benchmark_campaign_v1_1` had many top-level side folders
competing for attention.

After this pass, the reading model is clearer:
- front door
- contracts/plans/validation
- secondary reference
- archive links

## Secondary folders grouped in this pass

Moved under `40_supporting_reference/`:
- former scoring/Torch support
- former reference packs
- former future-method/future-architecture notes
- former legacy seed/solve reference

## Result

`benchmark_campaign_v1_1` is now much closer to the same reading model as
`rdp_v1`, while still keeping its richer benchmark-specific secondary material.
