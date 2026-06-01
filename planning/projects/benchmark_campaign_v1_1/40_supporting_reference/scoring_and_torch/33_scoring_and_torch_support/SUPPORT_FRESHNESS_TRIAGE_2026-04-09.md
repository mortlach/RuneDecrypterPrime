# Support freshness triage — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note classifies the current benchmark scoring/Torch support layers by
likely freshness and role.

## A. Likely still live support

These still look like active support notes for the benchmark campaign:

- `scoring_speed_investigation_2026-02-22.md`
- `torch_scoring_pipeline_upgrade_plan_v1.md`
- `scoring_contract_ecdf_abi.md`
- `README_TESTS_SCORING_2.md`

Why:
- they still relate directly to current scoring/backend discipline
- they line up with the current benchmark/scoring test surfaces already mapped
- they help explain current backend/parity reasoning

## B. Historical but still useful support

These still look useful, but more cautiously:

- `score_harden_v2.txt`
- `fully_torch_compliant_notes.txt`

Why:
- they may still contain relevant design intent
- but they read more like transitional hardening notes than core live campaign truth

## C. Candidate archive later

Nothing is being moved out in this slice.
But the most likely archive candidates later are:

- hardening notes that no longer match the current benchmark/scoring tests
- Torch-compliance notes if the upgrade path is superseded by a cleaner final state

## Working rule

For now:
- keep section A as active support
- keep section B as historical-but-useful support
- archive later only after a more explicit comparison against the current tests
