# Getting started

RDP separates what you know from what you want to find. With a known key, apply
`api.encrypt` or `api.decrypt` directly. With an unknown key, describe the allowed
candidates in a `KeySpec`: the solver searches them and the scorer ranks the
resulting plaintext. `RunSpec` keeps that request together.

The files below introduce those choices where they are used. Their comments
explain RDP concepts and useful alternatives, so you can adapt a nearby example
to your own question. Each file checks the specific outcome it describes.

The module commands below run from the repository root. They assume a source
checkout and a completed
[`installation`](../setup/installation.md).

## The first three stops

Run these in order:

```text
python -m tutorials.v1.getting_started.01_known_key
python -m tutorials.v1.getting_started.02_first_search
python -m tutorials.v1.getting_started.03_repeating_key_search
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
python -m tutorials.v1.getting_started.04_reproducible_runs
python -m tutorials.v1.getting_started.05_known_interruptors
python -m tutorials.v1.getting_started.06_partial_recovery
python -m tutorials.v1.getting_started.07_liber_primus_source
```

- `04` runs the same seeded request twice and checks its observable result.
- `05` treats known interruptor positions as evidence supplied to the request.
- `06` returns a stable partial result from an intentionally narrow budget. A
  completed run is not relabelled as an exact solve.
- `07` loads the named Welcome Pilgrim source through the public LP boundary.
  Loading source data is not the same operation as solving it.

## Read the evidence, then prepare a real case

```text
python -m tutorials.v1.getting_started.08_reading_a_result
python -m tutorials.v1.getting_started.09_changing_search_budget
python -m tutorials.v1.getting_started.10_prepare_a_real_source_search
```

- `08` separates the returned candidate, execution status, solver work,
  effective configuration, reproducibility and oracle record.
- `09` changes only beam width. Both searches recover the same answer, while
  the wider search performs more work; a larger budget is not a correctness
  certificate.
- `10` connects the named Welcome Pilgrim source to its reviewed cipher, key
  space, interruptor hypothesis, scorer and solver request. It deliberately
  prepares rather than launches the longer solve.

The companion [`anatomy of a run`](anatomy_of_a_run.md) explains these objects
as parts of one cryptanalytic claim.

## Run the release selection

```text
python tutorials/v1/run_tutorials.py
```

The default `RELEASE` group contains all ten stops plus columnar
transposition, repeating multiplication and scheduled-stream lookup examples.
The previous seven-stop selection took about 51 seconds on the reference CPU.
The expanded selection has not been timed as a whole; runtime depends on hardware.

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
