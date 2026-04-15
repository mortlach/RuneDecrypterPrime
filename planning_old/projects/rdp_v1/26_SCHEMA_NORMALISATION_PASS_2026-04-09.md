# Schema normalisation pass — 2026-04-09

Status: active
Work status: done
Project: rdp_v1

## What changed

This pass did not try to rewrite the whole project.

It did three focused things:

1. kept the front-door files intact
2. kept the main active/spec layers intact
3. collapsed the cluttered secondary layers behind:
   - `40_supporting_reference/`
   - `90_archive_links/`

## Why this matters

Before this pass, `rdp_v1` had many top-level side folders competing for
attention.

After this pass, the reading model is clearer:
- front door
- active/spec layers
- secondary reference
- archive links

## Secondary folders grouped in this pass

Moved under `40_supporting_reference/`:
- former support matrices
- former maintainer reference
- former integration history
- former scoring/assets history
- former forensic reference

## Result

`rdp_v1` is now the clearest model active home in the bundle.
