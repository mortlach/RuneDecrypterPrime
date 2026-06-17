# First real solve walkthrough

Status: user guide

This page explains one complete RDP tutorial at a beginner level.

The useful example is a ScheduledStreamLookup tutorial. It searches a real key
instead of simply being handed the final answer as the starting key.

## The idea

The tutorial has:

```text
ciphertext       the locked text
cipher model     ScheduledStreamLookup
searched key     a periodic key
supplied stream  a known sequence used by the cipher model
solver           tries candidate keys
scorer           ranks candidate plaintext
result           recovered key/text and pass/fail report
```

## Important distinction

```text
searched key     what the solver is trying to recover
supplied stream  extra cipher input, not the recovered key
```

Do not confuse those two.

## How to run tutorials

```text
python tutorials/v1/run_all.py
```

## Where to look next

```text
docs/guides/tutorial_catalogue.md
docs/guides/common_run_options.md
docs/guides/outputs.md
docs/expert/component_model.md
```

## What success means

A successful exact tutorial should report a complete match.

A successful near-solve tutorial should clearly state its acceptance threshold.

The tutorial manifest records those expectations:

```text
tutorials/v1/tutorial_manifest_v1.json
```
