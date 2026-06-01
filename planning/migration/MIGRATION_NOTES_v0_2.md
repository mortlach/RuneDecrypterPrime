# Migration notes — v0.2

This slice does two things:

1. tightens the `rdp_v1` project home with an explicit code-crosscheck note and
   a small active todo in the new format
2. creates the first proper `5455` problem brief under
   `p13_real_ciphertext_campaign`

This is still a controlled migration starter, not a full cut-over.

## What this slice still does not do

- no mass move into `legacy/`, `completed/`, or `archive/`
- no full rewrite of the promoted source docs
- no full result-log import for the p13 real-ciphertext project
- no attempt to make `rdp_v1` look more landed than it really is

## Why this slice matters

It turns two previously hand-wavy areas into concrete files:
- `rdp_v1`: what is landed, partly landed, or still target-state in the reviewed bundle
- `5455`: what the first named real-ciphertext problem thread actually hangs on
