# Benchmark Config Modules

This folder contains typed configuration modules that benchmark scripts import.

## Purpose

- Keep tuning values in explicit, reusable profile objects.
- Keep benchmark runners deterministic by avoiding ad-hoc runtime mutation.
- Make profile values easy to review and compare across benchmark scripts.

## Current Modules

- `no_wli_pipeline_profiles.py`
  - Defines no-WLI staged pipeline profiles.
  - Current production profile: `no_wli_a1_m12_b34_v1`.
  - Scorer schedule: `A_char1 -> M_char12 -> B_char34`.

## Usage Pattern

1. Benchmark script imports profile getter.
2. Script loads profile by id at startup.
3. Script copies profile values into local runtime config.
4. Script writes effective config to run output (`run_config.json`).

## Notes

- This module layer is benchmark-facing and does not change solver-core APIs.
- Other benchmark attack scripts can migrate to this pattern incrementally.

