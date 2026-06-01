# No-WLI Fixed-Instance Mode v1

Status note:

- completed and frozen as of `2026-04-14`
- this remains the baseline infrastructure contract
- the active no-WLI working contract is now:
  - `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_solver_development_v1_spec_2026-04-14.md`

This is the authoritative implementation contract for the first fixed-instance
infrastructure stream.

It supersedes the earlier reviewer-led background note now preserved under
`planning_old/legacy/no_wli_live_surface_residue_2026-04-14/source_docs/30_analysis_specs/next_steps_april_4_2026.txt`
as the working contract.

## Goal

Create a new no-WLI input mode where the benchmark instance is frozen and the
solver varies only by search seed.

In fixed mode, these two concepts must stay separate:

- source key seed
- search seed

They must never be conflated again.

## Scope of v1

### In scope

- export frozen fixed-instance fixtures from existing artifacts
- introduce fixed-instance schema and loader
- add fixed-instance mode to runtime
- add fixed-instance mode to the iteration loop
- add honest output identity and resume/proven plumbing
- land the first execution path through the fixture-matrix flow only
- create the first fixed panel manifest

### Out of scope

- solver experiments
- selector changes
- budget allocation changes
- stop-policy changes
- family-quality changes
- broad retrofitting of every old entrypoint

## Required new files

### 1. Fixed-instance schema

`tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_models.py`

Define:

- `FixedCipherInstanceSpec`
- optionally `FixedCipherPanelSpec`

### 2. Fixed-instance I/O

`tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_io.py`

Responsibilities:

- load fixture JSON
- validate schema version
- validate lengths
- validate `true_key_idx` length
- validate plaintext/ciphertext length consistency
- load panel manifest

### 3. Exporter

`tools/benchmarks/periodic_sub_trans/no_wli/export_fixed_instance_fixtures.py`

This must stay as an IDE-run script with a small hardcoded config block.
No CLI arguments.

Responsibilities:

- read existing final artifacts
- recover metadata
- recompute `true_key_idx` from `source_key_seed`
- verify re-encryption matches stored `ciphertext_idx`
- reconstruct `target_wli`
- write frozen fixture JSONs

### 4. Panel manifest

`tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json`

This is required in v1.

Reason:

- without it, the frozen instance set will drift immediately

## Required fixed-instance fixture schema

Use one JSON per frozen instance.

Required fields:

- `fixture_schema_version`
- `instance_fixture_id`
- `source_artifact_rel_path`
- `source_run_id`
- `source_fixture_id`
- `text_id`
- `source_key_seed`
- `offset_used`
- `period`
- `columns`
- `length`
- `alphabet_size`
- `direction`
- `order`
- `ciphertext_idx`
- `target_plaintext_idx`
- `target_wli`
- `true_key_idx`
- `notes`

### Non-negotiable rule

A frozen instance without `true_key_idx` is not acceptable.

That would create another half-finished mode.

## First fixed panel

Use these four frozen instances:

- `611`
- `1111`
- `1411`
- `1511`

The panel manifest must carry:

- panel id
- ordered instance fixture ids
- ordered search seeds
- short notes

## Required state/config changes

### In `runner_state_defaults.py`

Add:

- `INSTANCE_INPUT_MODE = "generated"` or `"fixed_ciphertext"`
- `INSTANCE_FIXTURE_IDS`
- `SEARCH_SEEDS`

Keep existing `KEY_SEEDS`, but generated mode only.

### Non-negotiable rule

Do not reuse `KEY_SEEDS` to mean search seed in fixed mode.

### In `run_config_builder.py`

Add explicit run-config fields for:

- `instance_input_mode`
- `instance_fixture_ids`
- `search_seeds`
- `generated_key_seeds`
- `text_offsets`

Generated mode and fixed mode must be distinguishable in the saved config.

## Required runtime changes

### In `iteration_runtime.py`

Generated mode must stay unchanged:

- draw true key from `key_seed`
- generate ciphertext from plaintext

Fixed mode must:

- load `ciphertext_idx`
- load `target_plaintext_idx`
- load `true_key_idx`
- build the cipher config from stored metadata
- verify decrypt/encrypt consistency
- compute oracle-derived helper values from the stored true key

### Non-negotiable rule

In fixed mode:

- `source_key_seed` is provenance only
- `search_seed` is the solver RNG input

## Required iteration-loop changes

### In `iteration_matrix_flow.py`

Generated mode must keep the current loop shape.

Fixed mode must loop over:

- tiers
- instance fixtures
- search seeds

It must not:

- slice plaintext on the fly
- regenerate ciphertext
- pretend the old generated loop is still the same with renamed fields

This is a real branch in the flow.

## Required identity/output changes

These are mandatory in the first landing:

- `artifact_resume.py`
- `run_summary.py`
- `autoskip_proven.py`
- payload/bridge builders
- final artifact naming
- stage/output row metadata

Required new fields everywhere relevant:

- `instance_input_mode`
- `instance_fixture_id`
- `instance_source_key_seed`
- `search_seed`

### Non-negotiable rule

Fixed mode must not be indexed or resumed as if it were still:

- `(text_id, key_seed)`

Generated mode identity remains based on:

- fixture
- text id
- key seed

Fixed mode identity must be based on:

- instance fixture id
- search seed

### Required output naming

For fixed mode, final artifact names must visibly distinguish:

- the frozen instance
- the search seed

Example:

- `fixture_001__p9_c3_l1000__text0__seed611__search7001.json`

Verbose is fine here. Honesty matters more than short names.

## Required tests

Create:

`tests/tools/test_no_wli_fixed_instance_mode.py`

Minimum required coverage:

### Exporter

- recomputed `true_key_idx` re-encrypts to stored `ciphertext_idx`
- reconstructed `target_wli` matches stored plaintext slice

### Runtime

- generated mode unchanged
- fixed mode uses stored ciphertext and key
- fixed mode roundtrip verification passes
- fixed mode oracle helpers are correct

### Iteration identity

- generated mode identity unchanged
- fixed mode identity uses `(instance_fixture_id, search_seed)`

### Outputs

- fixed-mode rows/artifacts contain the new identity fields

### Resume / proven

- no collisions between different search seeds on the same fixed instance
- no collisions between generated and fixed modes

These are not optional.

## Patch order

### Patch 1

Exporter + schema + panel manifest

Required landing:

- `fixed_instance_models.py`
- `fixed_instance_io.py`
- `export_fixed_instance_fixtures.py`
- `fixed_instance_panels/p9_c3_solver_panel_v1.json`

Do not proceed until the fixtures validate and re-encrypt correctly.

### Patch 2

State/config plumbing

Add:

- `INSTANCE_INPUT_MODE`
- `INSTANCE_FIXTURE_IDS`
- `SEARCH_SEEDS`

and run-config serialization for them.

### Patch 3

Runtime branch

Add generated vs fixed behaviour to `iteration_runtime.py`.

### Patch 4

Iteration-loop branch

Teach `iteration_matrix_flow.py` to iterate over fixed instances x search
seeds.

### Patch 5

Identity/output/resume/proven plumbing

This is mandatory in the first landing.
Do not delay it.

### Patch 6

First fixture-matrix execution path

Use the new mode through the fixture-matrix path only.
Do not broaden entrypoint support yet.

## Explicitly forbidden shortcuts

- no "fixed mode first, resume later"
- no "fixed mode first, honest output fields later"
- no "just store ciphertext and regenerate the rest somehow"
- no overloading `FixtureSpec`
- no overloading `KEY_SEEDS`
- no solver experiments before the exporter/schema/runtime branch is solid
