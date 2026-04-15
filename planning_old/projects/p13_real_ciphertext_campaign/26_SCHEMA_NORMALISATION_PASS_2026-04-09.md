# Schema normalisation pass — 2026-04-09

Status: active
Work status: done
Project: p13_real_ciphertext_campaign

## What changed

This pass kept the home intentionally light.

It did three focused things:

1. kept the front-door files intact
2. grouped thread-specific material into:
   - `10_active_plans/`
   - `20_specs_and_analysis/`
   - `30_status_and_results/`
3. pushed broader context behind:
   - `40_supporting_reference/`
   - `90_archive_links/`

## Why this matters

Before this pass, the project had separate folders that were historically clear
but less aligned with the new common reading model.

After this pass, the reading model is clearer:
- front door
- thread plans
- thread specs
- thread status/results
- context only after that

## Secondary folders grouped in this pass

Moved under `20_specs_and_analysis/`:
- former problem briefs
- former analysis specs

Moved under `30_status_and_results/`:
- former run logs

Moved under `40_supporting_reference/`:
- former broader reference context

## Result

`p13_real_ciphertext_campaign` is now aligned to the common schema while staying
thin and downstream.
