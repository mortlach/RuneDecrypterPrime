# Community benchmark reference bundle pass — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note reviews the older benchmark reference bundle now preserved under:

- `35_reference_packs/community_benchmark_v1_1_spec_bundle/`

## Purpose of this pass

The goal is not to re-open the whole old bundle as if it were the live project.

The goal is to say more clearly:
- what still helps the current benchmark home
- what is mainly historical context
- what looks likely to stay reference-only

## Current judgement by sub-area

### A. Still useful as live reference support

These parts still look useful as supporting reference while the benchmark home
remains active:

- `tools/benchmarks/community/README*.md`
- `tools/benchmarks/community/campaign_spec_v1_1.md`
- `docs/setup/setup_and_preflight_v1_1.md`
- `tools/benchmarks/community/schemas/*.json`
- `tools/benchmarks/community/examples/*.json`

Why:
- they still map naturally to current campaign setup, schemas, and organiser/runner
  expectations
- they help explain the shape of the benchmark campaign without outranking the
  current live pack

### B. Historical but still useful reference

These still look worth keeping, but mainly as older rollout/history context:

- `COMMUNITY_TO_V1_TODO.md`
- `PHASE0_REVIEW_GATE.md`
- `phase2_files/PROGRESS_NOTES.md`
- `phase3_files/PROGRESS_NOTES.md`
- phase-local tool/test snapshots under `phase2_files/` and `phase3_files/`

Why:
- they help explain how the campaign bundle evolved
- but they are not the present truth of the project home

### C. Reference-only and likely never part of the live pack

These should remain reference-only and should not try to behave like active docs:

- `assets_manifest_v1.json`
- `prompt.txt`
- fixture sample files used as bundle scaffolding
- phase-local duplicated tool/test snapshots once their role is only historical

Why:
- they are useful for reconstruction and provenance
- but not necessary for the live benchmark entry pack

## Practical conclusion

The older benchmark reference bundle is now good enough to keep as:

- **live reference support** for a small subset
- **historical reference** for the rest

This means it no longer blocks day-to-day use of the benchmark project home.

It still makes sense to keep the whole bundle preserved, but it does not need to
be promoted further into the live pack right now.
