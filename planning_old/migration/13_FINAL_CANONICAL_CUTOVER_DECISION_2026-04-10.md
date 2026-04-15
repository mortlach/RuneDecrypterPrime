# Final canonical cut-over decision - 2026-04-10

This note records the final explicit cut-over decision for repo-wide planning.

## Decision

Use `planning/` as the canonical planning system for
repo-wide work.

That means:
- start from `00_PORTAL.md`
- use the active project homes under `projects/`
- treat old top-level planning surfaces as retired history, not current entry
  points

## Explicit exceptions

Two things remain outside the canonical bundle on purpose:
- `planning/no_wli/`
  - upstream live home
- `planning/working/`
  - deprecated compatibility stub only

Neither of these changes the canonical read order for repo-wide planning.

## Why this is now safe

The cut-over criteria in `07_CANONICAL_CUTOVER_CRITERIA.md` are met:
- the active homes have stable live packs
- support/reference layers are clearly secondary
- the cross-project control layer is readable
- old top-level planning surfaces no longer compete with the live homes

The main old surfaces are now retired:
- `planning/drafts/`
- `planning/review/`
- `planning/old/`
- the pre-promotion standalone archive wrapper
- `planning/v1/`
- `planning/plna_refactor/`

Preserved historical material now lives inside:
- `planning/archive/`
- `planning/completed/`
- `planning/legacy/`

## Practical rule

For normal planning work:
1. start in `planning/`
2. move into the relevant active project home
3. only leave the canonical bundle if:
   - an active document explicitly sends you to archive/reference material, or
   - you are working in the explicit upstream `planning/no_wli/` home

## What this decision does not say

It does not say:
- every support note is permanently in the right place
- `planning/no_wli/` must be absorbed into this bundle
- no later archive trimming will be needed

It only says the repo now has one canonical planning system.
