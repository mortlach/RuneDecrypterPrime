# Cross-seed and focus-family summary

Date: 2026-04-14

Option A highlights:

- `611`: two clearly single-family late regions (`7004`, `7005`), with mixed-family behavior on the other runs.
- `1111`: the most fragmented seed in this pack by the family-mapped stage35 rows. Mean distinct-family count is `2.0`, and only `7002` is single-family.
- `1411`: one solved run (`7003`) has archive-side stage35 seed rows but no family-mapped stage35 rows in `best` / `space_map`; the other runs are mostly either `f0`-only or `f0:1, f1:5`.
- `1511`: the tightest non-solved late-family pattern in this pack. `7002`, `7003`, and `7004` are single-family, and the mean dominant-family share is about `0.958` on runs with family-mapped stage35 rows.
- Solved runs are not symmetric with unsolved runs: `1411/7003` and `1511/7001` still retain archive-side stage35 seed rows, but they have no family-mapped stage35 rows on the `best` / `space_map` side.

Option B highlights:

- The `1111` focus family is `f0` in all five runs.
- `7002` is the cleanest `1111/f0` case: all six family-mapped stage35 rows are in `f0`, and the focus family reaches max final match `0.752` with max final score `0.3022291305585272`.
- `7003` and `7005` remain `f0`-dominant (`5/6` stage35 rows), but their focus-family max final scores are much lower: `0.16151737726005755` and `0.1466989954364033`.
- `7004` is the fragmented case: stage35 rows split across `f0:1, f1:1, f2:3` even though the top admitted family still lands in `f0`.
- `7001` shows the inverse pattern: the focus family is still `f0`, but the family-mapped stage35 rows are dominated by `f1:5`.

Suggested reviewer path:

1. Use `10_option_a_cross_seed_stage35_family/01_cross_seed_seed_summary.csv` to compare how concentrated each seed's late-family region is.
2. Use `10_option_a_cross_seed_stage35_family/00_cross_seed_run_summary.csv` to locate the specific runs worth drilling into.
3. Use `20_option_b_1111_focus_family_context/00_1111_focus_family_run_summary.csv` for the `1111/f0` overview.
4. Use `20_option_b_1111_focus_family_context/02_1111_focus_family_anchor_rows.csv` and the per-run files under `10_per_run/` for the row-level diagnostic read.
