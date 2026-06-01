# No-WLI late-family-quality v2 spec

Date: 2026-04-08

## Purpose

Build `late_family_quality_v2` as a frozen-input agreement/disagreement study
on top of:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`

Study exactly six seeds:

- discriminator trio:
  - `1111`
  - `1311`
  - `1411`
- reference wins:
  - `411`
  - `611`
  - `1011`

Work at the seed level.

Compare the winner families for:

- truth
- trust
- archive uplift
- full uplift
- persistence

Emit:

- one seed-level agreement row per seed
- one pairwise comparison row per seed and metric pair
- one summary json
- one short markdown case report

Do not:

- mutate stop logic
- widen the seed set
- promote a score head

Main question:

Which winner-family split patterns look acceptable for real wins, and which
look suspicious?
