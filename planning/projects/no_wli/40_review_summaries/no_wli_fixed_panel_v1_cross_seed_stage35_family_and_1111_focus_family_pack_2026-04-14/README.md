# No-WLI fixed panel v1 cross-seed stage35-family and 1111 focus-family pack

Date: 2026-04-14

This pack extends the retained 20-job fixed-panel review material in two ways.

Option A:
- cross-seed stage35-family summaries for `611`, `1111`, `1411`, and `1511`
- per-seed run summaries, per-run joined extracts, and copied raw `stage35` artifacts
- one cross-seed run summary and one seed summary for quick comparison

Option B:
- row-level `stage3` diagnostics for the `1111` focus family around the top stage35-admitted family in each run
- per-run family summaries plus focus-family row extracts for deeper diagnostic review

Pack layout:
- `10_option_a_cross_seed_stage35_family/`
- `20_option_b_1111_focus_family_context/`

Read order:
1. `README.md`
2. `01_summary_for_reviewers.md`
3. `10_option_a_cross_seed_stage35_family/00_cross_seed_run_summary.csv`
4. `10_option_a_cross_seed_stage35_family/01_cross_seed_seed_summary.csv`
5. `20_option_b_1111_focus_family_context/00_1111_focus_family_run_summary.csv`
6. `20_option_b_1111_focus_family_context/01_1111_all_family_summary.csv`
7. `20_option_b_1111_focus_family_context/02_1111_focus_family_anchor_rows.csv`
