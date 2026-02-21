# Community Config Layer (v1.1)

This folder is the human-facing configuration layer for community benchmark tuning.

## Why this exists
- Keep tuning semantics separate from runner/cipher/logging logic.
- Make profile knobs explicit and documented.
- Provide bounded ranges for safe random exploration.

## File layout
- `ranges_v1_1.json`
  - Canonical list of supported knobs.
  - Label + meaning + value type + recommended ranges.
  - Includes `sampling_spaces.community_safe` for randomized profile generation.
- `knob_reference_v1_1.md`
  - Reviewer-facing markdown table generated from `ranges_v1_1.json`.
  - Quick scan of key, meaning, value type, defaults, and bounds.
- `profile_config.py`
  - Dataclasses for profile catalog and knob ranges.
  - Validation of profile overrides against allowed keys and ranges.
  - Single function to apply validated overrides into pipeline modules.
- `build_knob_reference.py`
  - Regenerates `knob_reference_v1_1.md` from `ranges_v1_1.json`.
- `sampler.py`
  - Deterministic random profile sampler using `ranges_v1_1.json`.
  - Produces profile snippets compatible with `profile_catalog_v1_1.json`.

## Human workflow
1) Read `ranges_v1_1.json` to see:
- what each config setting means,
- which values are safe,
- which knobs are basic vs advanced.

2) Edit or generate profile rows:
- manual edit in `profile_catalog_v1_1.json`, or
- generate candidates with `sampler.py`.

Regenerate the markdown reference table:

```powershell
python tools/benchmarks/community/config/build_knob_reference.py
```

Example sampler command:

```powershell
python tools/benchmarks/community/config/sampler.py `
  --base-profile-id stage3_fullband_basin_v1_1 `
  --count 8 `
  --seed 20260220 `
  --out tools/benchmarks/community/examples/sampled_profiles_v1_1.json
```

3) Run campaign tools:
- runner/job code loads and validates profile catalog through `profile_config.py`.

## Notes
- `PIPELINE_DEFAULT` means "do not override that knob".
- `null` is used only when the knob meaning explicitly supports disabling (for example stage3 gates).
