# P13 source crosswalk and upstream status - 2026-04-10

Status: active
Work status: in_progress
Project: p13_real_ciphertext_campaign

## Purpose

This note records:
- which older source surfaces fed this home
- which upstream no-WLI references are deliberate
- which old-path mentions are only preserved historical provenance
- whether live thread files still depend on scattered raw upstream path lists

## Main source surfaces

Primary project inputs:
- thread-specific notes promoted into this home
- `planning/no_wli/` as the live upstream method-development home
- selected older no-WLI/p13 context files preserved under
  `40_supporting_reference/reference_context/`

## Deliberate upstream references

These are not migration debt:
- `90_archive_links/NO_WLI_UPSTREAM_LINK.md`
- `20_specs_and_analysis/analysis_specs/30_analysis_specs/no_wli_upstream_reference_policy.md`
- `20_specs_and_analysis/analysis_specs/30_analysis_specs/5455_pinned_upstream_anchors_v1.md`

Reason:
- this home is intentionally downstream of `no_wli`
- it should stay honest about what remains upstream

## Historical provenance only

The preserved readiness-context pack includes old no-WLI path citations such as:
- `planning/working/no_wli_*`
- `planning/old/no_wli_legacy_migration_2026-04-04/...`

Those references are kept as source provenance inside preserved context files.
They are not supposed to function as the live reading path for this home.

## Current live-link hygiene rule

Thread-facing docs should prefer:
1. the local front-door files
2. `5455_pinned_upstream_anchors_v1.md` for exact upstream anchors
3. `no_wli_upstream_reference_policy.md` for role boundary
4. `90_archive_links/NO_WLI_UPSTREAM_LINK.md` for the live upstream home route

They should avoid repeating raw no-WLI path lists unless a note is specifically
about pinning those exact anchors.

## Specific absorbed old-pack case

The small deep-research pack under:
- `planning/old/no_wli_legacy_migration_2026-04-04/review_and_research_packs/no_wli_deep_research_pack_2026-03-21/`

is now treated as absorbed into:
- `40_supporting_reference/reference_context/35_reference_context/p13_readiness_context/`

That means the old pack is provenance-only once its preserved copies are in
place. It is not a live reading surface for this home.

## Current judgement

This home is structurally fine.
The remaining work is path hygiene only:
- centralise repeated upstream references
- keep preserved historical no-WLI citations secondary
- avoid turning upstream context packs into fake direct `5455` thread history
