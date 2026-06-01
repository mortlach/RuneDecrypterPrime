# Current state

Status: active
Work status: in_progress
Project: p13_real_ciphertext_campaign

## Short read

`p13_real_ciphertext_campaign` is the downstream real-ciphertext p13 thread home.

This project is intentionally thinner than the other active homes.
It now has a cleaner shape:

- a front-door live pack
- thread-specific plans/specs/status layers
- one small grouped supporting-reference layer
- an upstream link kept behind the live pack

## Verified code-facing anchors in the reviewed bundle

### Landed enough to treat as real
- `tests/data/test_lp_master_transcript.py`
  - transcript/API parity surface
- `src/rune_decrypter_prime/api/data_helpers.py`
  - LP helper route including `load_lp_master_section`
- solve-proof support files under:
  - `tools/benchmarks/solve_proof/`

### Real but intentionally thin
- this home is downstream of `no_wli`
- it contains thread-specific control/result scaffolding
- it is not supposed to become the main p13 method-development home
- upstream no-WLI reference handling is explicit inside this home

### Still not claimed here
- no real-ciphertext solve result
- no broad p13 ownership beyond the downstream thread role

## Main planning need

Use this home as the clean downstream thread surface:
- front-door files first
- active plans second
- specs/analysis third
- status/result notes fourth
- supporting reference only after that
- upstream/crosswalk note only when checking no-WLI linkage or historical residue
