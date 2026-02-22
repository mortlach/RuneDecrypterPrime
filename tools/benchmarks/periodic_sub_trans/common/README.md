# Common Utilities

Shared runner infrastructure lives here:

- output path helpers
- report writing helpers
- final artifact save/restore
- proven solve log helpers
- telemetry flatten/projection helpers

The goal is to remove copy-paste across flavor runners while keeping behavior deterministic.

Utilities:

- `migrate_legacy_outputs.py`: copy old root-level benchmark run folders into
  `output/tools/benchmarks/periodic_sub_trans/<flavor>/legacy_import/`.
- `port_legacy_solve_history.py`: import rows from legacy generic solve-proof
  history into flavor-specific history logs (append-only, deduped).

