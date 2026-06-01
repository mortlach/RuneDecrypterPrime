# 5455 problem brief

Status: active
Work status: in_progress
Project: p13_real_ciphertext_campaign

## Why this thread exists

`5455` is the first named attach-on thread for the real-ciphertext p13 campaign.

This project home keeps that thread separate from:
- the general benchmark/community learning campaign
- the upstream no-WLI solver-development stream

## Verified code anchors in the reviewed bundle

### A. Pages 54 and 55 are already treated as a real LP data boundary in tests
Confirmed test file:
- `tests/data/test_lp_master_transcript.py`

Confirmed test behaviour:
- `test_pages_54_55_match_old_5455`
- `test_pages_54_55_span_matches_master_section_and_crosses_boundary`

Those tests treat pages `54.jpg` and `55.jpg` as one meaningful span and check
that the span crosses the page boundary without breaking the word-link mapping.

### B. The pages 54–55 span is tied to master section 13
Confirmed test behaviour:
- `load_lp_master_section(13, split="page")` is compared against the direct
  transcript span for pages 54 and 55
- the test asserts `len(ct_api) == 308`

Interpretation:
- there is already a code-backed way to talk about this problem span as a real,
  deterministic payload source

### C. API helper exists for pulling that payload
Confirmed file:
- `src/rune_decrypter_prime/api/data_helpers.py`

Confirmed helper:
- `load_lp_master_section(section_id, split="page")`

This matters because it means the p13 real-ciphertext campaign can point to a
typed payload path rather than only to old ad-hoc notes.

## Current planning interpretation

For planning purposes, `5455` should be treated as:
- a named real-ciphertext problem thread
- one concrete frontier problem inside the broader p13 real-ciphertext campaign
- downstream of no-WLI method-development rather than a replacement for it

## Immediate planning need

The first useful `5455` pack should stay small:

1. this problem brief
2. one compact current-status note
3. one active plan for first campaign work
4. one result log or status ledger
5. explicit links back to no-WLI and solve-proof evidence

## What is still missing

Not yet added in this slice:
- a dedicated `5455` run log
- a compact best-evidence ledger
- a mapped list of every old note that belongs to this thread
