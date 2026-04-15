# Fixed-Instance Solver Development v1 Plan

Question:

- for one fixed ciphertext instance, what changes in the pipeline actually
  improve solving, and where does the good path get lost?

Scope:

- baseline digest for the frozen fixed panel
- `1111` conversion-failure audit
- `1511` positive-control audit
- `611` middle-case audit
- `1411` caveat note
- one or two justified solver-change candidates only after those audits

Execution:

- read the three frozen review packs from hardcoded repo-relative paths
- build deterministic panel baseline rows
- keep `archive_seed_row_count`, `best_stage35_seed_row_count`, and
  `space_map_stage35_row_count` separate
- keep `focus family`, dominant mapped stage35 family, and final-best family
  separate
- write the required machine-readable comparison tables and short markdown
  memos
- only after that, write a narrow candidate-change shortlist

Constraints:

- no CLI arguments
- no latest-bundle discovery
- no live runs
- no runtime or solver tuning before the baseline and audit outputs exist
