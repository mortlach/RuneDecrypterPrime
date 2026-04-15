# Late Family Quality v1

The full contract for this branch lives in:

- `planning/projects/no_wli/30_analysis_specs/no_wli_late_family_quality_v1_spec_2026-04-08.md`

This analysis reads a frozen `score_stop_shadow_v2` bundle and studies exactly
six seeds at the family level over:

- `phaseC_start`
- `stage35_seed`
- `stage35_archive`

The question is:

Does family-level late behaviour separate the accepted miss (`1111`) from the
two false-fire shapes (`1311`, `1411`) more cleanly than the current row-level
stop harness does?

Scope:

- offline only
- fixed input bundle
- fixed seed set
- no stop-logic mutation
- no reclustering
- no new live seeds

Primary outputs:

- `family_quality_rows.jsonl`
- `family_quality_case_digest.jsonl`
- `family_quality_summary.json`
- `family_quality_cases.md`

