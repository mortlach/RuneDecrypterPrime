# RDP v1 support freshness crosscheck — 2026-04-09

Status: active
Work status: done
Project: rdp_v1

This note cross-checks the current `rdp_v1` support layers against the active
project role and the code-facing surfaces already confirmed in the bundle.

## Current code-facing anchors already confirmed

The `rdp_v1` home already has code-facing anchors for:
- API/spec surface
- core problem spec surface
- scoring report surface
- LP-facing API/data helper surface
- benchmark/campaign machinery still living under `tools/`

Interpretation:
- support material is justified only if it helps explain or manage that
  convergence work
- support material should not survive merely because it exists

## File-by-file freshness judgement

### A. Keep as active support for now

#### `rdp_v1_feature_support_matrix_draft_2026-03-10.csv`
Why:
- still useful for feature/convergence visibility
- directly tied to "what is in v1 versus later" reasoning

Judgement:
- keep as active support

#### `rdp_v1_current_code_mapping_note_template_v1_2026-03-11.md`
Why:
- directly supports code-to-planning mapping work
- still useful while convergence is incomplete

Judgement:
- keep as active support

#### `RDP_v1_current_code_mapping_note_6.txt`
Why:
- directly tied to current-code mapping
- still useful as historical support for current mapping work

Judgement:
- keep as active support for now

#### `support-to-test_map_7.txt`
Why:
- directly helps connect support claims to tests
- still useful while project convergence remains evidence-driven

Judgement:
- keep as active support

#### `support_matrix_cell_meanings_5.txt`
Why:
- necessary companion to the support matrix while it remains in use

Judgement:
- keep as active support

#### `findings_register.csv`
Why:
- still useful as a structured findings/support record
- directly relevant to convergence tracking

Judgement:
- keep as active support

### B. Keep as historical-but-useful support for now

#### `rdp_v1_method_families_and_feature_matrix_2026-03-10.xlsx`
Why:
- useful structured workbook for method-family, capability, and open-item context
- supports the support-matrix reading, but should not outrank the active text pack

Judgement:
- historical but useful support

#### `change_workflow_4.txt`
Why:
- useful as process history
- less directly tied to current code surface

Judgement:
- historical but useful support

#### `Effor_Bands_3.txt`
Why:
- useful for planning/process context
- not central to present code-facing truth

Judgement:
- historical but useful support

#### `RDP_v1_convergence_implementation_plan_2.txt`
Why:
- useful as older implementation-planning context
- but more transitional than canonical

Judgement:
- historical but useful support

#### `the_real_implmentation_plan_1.txt`
Why:
- useful as implementation-history context
- but not something that should outrank the current live pack

Judgement:
- historical but useful support

#### `maintainer_handbook_v2.txt`
Why:
- still useful to retain
- but clearly secondary to the active home

Judgement:
- historical but useful support

#### `rdp_private_maintainer_handbook_skeleton_2026-03-09.md`
Why:
- still possibly useful as reference
- but visibly more provisional than a live canonical document

Judgement:
- historical but useful support
- likely archive candidate later if it remains skeletal

## Overall judgement

The `rdp_v1` support layer should remain under the active home, but with a
clearer split:

- active support:
  - feature support matrix
  - current-code mapping template and note
  - support-to-test map
  - support-matrix cell meanings
  - findings register

- historical but useful support:
  - workflow/effort-band notes
  - older implementation-plan text notes
  - maintainer reference docs

## What this does not yet do

This note does **not** move any files to archive yet.
It only makes the freshness judgement explicit.
