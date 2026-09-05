# Getting started

This is an ordered route through ordinary RDP use. Each file is a small,
runnable claim backed by an assertion.

All commands assume a source checkout and a completed
[`installation`](../setup/installation.md).

## The first three stops

Run these in order:

```text
python tutorials/v1/getting_started/01_known_key.py
python tutorials/v1/getting_started/02_first_search.py
python tutorials/v1/getting_started/03_repeating_key_search.py
```

They establish three different things:

1. a cipher and a known key can round-trip a reviewed rune-index message;
2. a `RunSpec` can ask RDP to recover a small unknown key;
3. the same public request shape handles a repeating key and raw rune text with
   word boundaries.

The distinction matters. Applying a supplied key is an operation. Recovering a
key is a scored search.

## Continue when the first shape is clear

```text
python tutorials/v1/getting_started/04_reproducible_runs.py
python tutorials/v1/getting_started/05_known_interruptors.py
python tutorials/v1/getting_started/06_partial_recovery.py
python tutorials/v1/getting_started/07_liber_primus_source.py
```

- `04` runs the same seeded request twice and checks its observable result.
- `05` treats known interruptor positions as evidence supplied to the request.
- `06` returns a stable partial result from an intentionally narrow budget. A
  completed run is not relabelled as an exact solve.
- `07` loads the named Welcome Pilgrim source through the public LP boundary.
  Loading source data is not the same operation as solving it.

## Run the release selection

```text
python tutorials/v1/run_tutorials.py
```

The default `RELEASE` group contains all seven stops plus columnar
transposition, repeating multiplication and scheduled-stream lookup examples.
On the reference CPU used for this migration it completed in about 51 seconds.

The runner is intentionally edited in one place. To run only the ordered route,
set:

```python
RUN_SET = TutorialRunSet.GETTING_STARTED
```

To print each subprocess output in full, set:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

There are no command-line flags or environment-variable aliases for this
choice. The value in the file is the value being reviewed.

## Read results without flattering them

Check, in roughly this order:

1. recovered text and key;
2. exact or thresholded reference agreement when known truth is available;
3. execution status, stop category and stop reason;
4. the requested and effective seed;
5. scoring and solver configuration;
6. whether truth or an oracle affected setup, stopping or only validation.

A score ranks candidates under a configured model. It is evidence, not a
certificate of plaintext.

Continue with [`runes and text`](runes_and_text.md), then choose a worked case
from the complete [`example catalogue`](../../tutorials/v1/README.md).
