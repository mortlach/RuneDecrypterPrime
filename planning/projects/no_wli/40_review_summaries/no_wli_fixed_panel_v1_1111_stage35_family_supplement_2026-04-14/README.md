# No-WLI fixed panel v1 1111 stage35 family supplement

Date: 2026-04-14

This supplement packages the per-run `stage35` seed-row artefacts for the five
`1111` fixed-instance runs and joins them to the retained family ids.

What is included:

- reviewer summary in `01_summary_for_reviewers.md`
- source pointer manifest in `02_source_pointer_manifest.csv`
- one combined joined CSV for all five runs in `03_all_1111_stage35_family_join.csv`
- per-run joined CSV and JSONL files in `10_joined_stage35_family/`
- copied raw `stage35_seed_archive.json` and `stage35_progress.jsonl` files in
  `20_raw_stage35_seed_artifacts/`

Important note:

- a ready-made per-run atlas/family export was not found inside the retained
  bundles
- the retained bundles do contain the two source layers needed to reconstruct
  that view cleanly:
  - `resume_handoffs/.../stage35_seed_archive.json`
  - `best/best_instance.json` under both `stage35_seed_rows` and
    `stage3_diagnostics.space_map_v1.partial_state_rows`
- the raw archive `candidate_hash` is not the same as the family-bearing
  `candidate_hash` in `best/best_instance.json`
- this supplement bridges that using the preserved per-row identity tuple:
  `stage3_rank + source_rank + stage3_source + seed_source`
- once bridged to `best/stage35_seed_rows`, the family join to the space-map row
  is direct via `candidate_hash`

Read order:

1. `README.md`
2. `01_summary_for_reviewers.md`
3. `02_source_pointer_manifest.csv`
4. `03_all_1111_stage35_family_join.csv`
5. per-run files in `10_joined_stage35_family/`
