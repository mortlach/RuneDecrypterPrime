# Community Config Reference (v1.1)

Generated from `ranges_v1_1.json`.

| Key | Label | Type | Default | Range | Mode | Meaning |
| --- | --- | --- | --- | --- | --- | --- |
| `stage3_gating.full_entry_score` | Stage3 Full Entry Score | `float_or_null_or_default` | `PIPELINE_DEFAULT` | value: [0.0, 1.0] | `basic` | Score threshold for entering full Stage-3 refinement. null disables this gate. |
| `stage3_gating.probe_entry_score` | Stage3 Probe Entry Score | `float_or_null_or_default` | `PIPELINE_DEFAULT` | value: [0.0, 1.0] | `basic` | Score threshold for entering probe Stage-3 mode. null disables probe gating. |
| `stage12_carry_through.promote_top` | Stage1/2 Promote Top | `int_or_default` | `PIPELINE_DEFAULT` | value: [1, 128] | `basic` | How many top candidates are promoted from Stage-1/2 into later refinement. |
| `stage12_carry_through.archive_keep` | Stage1/2 Archive Keep | `int_or_default` | `PIPELINE_DEFAULT` | value: [1, 256] | `basic` | How many candidates are retained in the Stage-1/2 archive. |
| `stage1_breadth.sub_candidates_by_columns` | Stage1 Sub Candidates by Columns | `int_map_or_default` | `PIPELINE_DEFAULT` | map values: [1, 256]; map keys: {1, 3, 5, 7, 10, 13} | `basic` | Per-column candidate breadth for Stage-1 substitution exploration. |
| `stage3_basin_exploration.initial_keys_by_columns` | Stage3 Initial Keys by Columns | `int_map_or_default` | `PIPELINE_DEFAULT` | map values: [1, 256]; map keys: {1, 3, 5, 7, 10, 13} | `basic` | Per-column number of Stage-3 starting keys for basin diversity. |
| `solver_stage1` | Solver Stage1 Override | `dict_or_default` | `PIPELINE_DEFAULT` | - | `advanced` | Advanced direct override map for SOLVER_STAGE1 (use with care). |
| `solver_stage2` | Solver Stage2 Override | `dict_or_default` | `PIPELINE_DEFAULT` | - | `advanced` | Advanced direct override map for SOLVER_STAGE2 (use with care). |
| `solver_stage3` | Solver Stage3 Override | `dict_or_default` | `PIPELINE_DEFAULT` | - | `advanced` | Advanced direct override map for SOLVER_STAGE3 (use with care). |

## Sampling Spaces

- `community_safe`: Conservative randomized search space for friendly community benchmarking.
