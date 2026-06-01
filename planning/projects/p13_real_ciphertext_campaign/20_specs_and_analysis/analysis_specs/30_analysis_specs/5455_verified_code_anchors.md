# 5455 verified code anchors

Status: active
Work status: done
Project: p13_real_ciphertext_campaign

This note records the concrete source/test anchors already found for the `5455`
thread in the reviewed bundle.

## Source files copied into evidence snapshots

- `tests/data/test_lp_master_transcript.py`
- `src/rune_decrypter_prime/api/data_helpers.py`

## Verified anchors

### 1. Test-level anchor: pages 54–55 are treated as one meaningful span
Confirmed test names:
- `test_pages_54_55_match_old_5455`
- `test_pages_54_55_span_matches_master_section_and_crosses_boundary`

### 2. Section-level anchor: the same span is linked to section 13
Confirmed call:
- `load_lp_master_section(13, split="page")`

### 3. Size anchor: the test expects 308 ciphertext indices
Confirmed assertion:
- `assert len(ct_api) == 308`

### 4. API helper anchor: deterministic payload helper exists
Confirmed helper:
- `load_lp_master_section(...)` in `src/rune_decrypter_prime/api/data_helpers.py`

## Important caution

The reviewed bundle did not expose the old `src/.../old/5455.py` source file
that one of the tests refers to.

So the safe statement here is:
- the test clearly expects legacy `5455` parity
- but the old raw source file itself was not verified from the reviewed bundle
