# 1111 run supplement summary

Date: 2026-04-14

This supplement covers the five `1111` runs from the fixed 20-job panel.

Join method:

- raw stage35 seed rows are copied from `resume_handoffs/.../stage35_seed_archive.json`
- the family-bearing stage35 rows come from `best/best_instance.json` under `stage35_seed_rows`
- family ids come from `best/best_instance.json` at `stage3_diagnostics.space_map_v1.partial_state_rows` filtered to `replay_config_ref = stage35_seed_rows`
- archive rows are bridged to best rows by `stage3_rank + source_rank + stage3_source + seed_source`
- best rows are bridged to family ids by `candidate_hash`

Coverage check:

- all five `1111` runs had complete retained artefacts
- total joined rows across the five runs: 29
- archive-to-best bridging was complete for all five runs
- best-to-space family matching by `candidate_hash` was complete for all five runs

Per-run family counts:

- search 7001: 6 joined rows; family counts f0:1, f1:5
- search 7002: 6 joined rows; family counts f0:6
- search 7003: 6 joined rows; family counts f0:5, f1:1
- search 7004: 5 joined rows; family counts f0:1, f1:1, f2:3
- search 7005: 6 joined rows; family counts f0:5, f1:1

Use `03_all_1111_stage35_family_join.csv` for a quick panel-wide scan, then drop into the per-run CSV/JSONL files when the reviewer wants raw row context.
