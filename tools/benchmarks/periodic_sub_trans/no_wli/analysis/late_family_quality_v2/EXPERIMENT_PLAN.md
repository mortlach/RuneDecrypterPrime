# Experiment Plan

Input bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`

Study seeds:

- discriminators: `1111`, `1311`, `1411`
- reference wins: `411`, `611`, `1011`

Execution stance:

- seed-level only
- no stop-rule mutation
- no reclustering
- deterministic pattern normalization across:
  - truth
  - trust
  - archive uplift
  - full uplift
  - persistence

Success condition:

- the study cleanly distinguishes which split patterns recur in real wins and
  which look suspicious in the discriminator trio
