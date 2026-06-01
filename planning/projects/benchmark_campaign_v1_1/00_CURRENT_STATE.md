# Current state

Status: active
Work status: in_progress
Project: benchmark_campaign_v1_1

## Short read

`benchmark_campaign_v1_1` is the general community benchmark and p13-learning
campaign home.

This project is no longer mainly blocked on finding documents.
It now has a cleaner shape:

- a front-door live pack
- contract/plan/validation layers
- one grouped supporting-reference layer
- archive links kept behind the live pack

## Verified code-facing anchors in the reviewed bundle

### Landed enough to treat as real
- `tools/benchmarks/community/`
  - organiser, runner, config and validation machinery
- `tests/community/`
  - schema/workflow/preflight tests
- scoring-path tests including:
  - `test_avg_ecdf_runtime_separation.py`
  - `test_score_parity_torch.py`
  - `test_backend_selection_and_parity.py`

### Real but not fully simplified yet
- benchmark source-pack crosswalk is now explicit inside this home
- many useful secondary clusters were rescued and preserved
- the main absorbed benchmark duplicates in `planning/drafts/` are retired
- the project now needs the two leftover non-benchmark draft files to be
  classified, plus broader old-cluster cleanup, more than more discovery

### Not the role of this project
- repo-level release truth for `rdp_v1`
- downstream real-ciphertext thread truth for `5455`
- live no-WLI method-development ownership

## Main planning need

Use this home as the clean benchmark/p13-learning surface:
- front-door files first
- contracts/plans/validation second
- grouped supporting-reference only after that
- source-crosswalk note only when retiring old draft paths
