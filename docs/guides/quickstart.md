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

In these files we:

1. encrypt a message and decrypt it with the key we already know;
2. give RDP ciphertext and a range of rail counts, then ask it to find the key;
3. use the same `RunSpec` approach to find a repeating key, this time starting
   from visible rune text with spaces.

The first file supplies the key. In the next two, the solver has to find it
by trying candidates and using the scorer to judge the decrypted text.

## Add a few more choices

```text
python -m tutorials.v1.getting_started.04_reproducible_runs
python -m tutorials.v1.getting_started.05_known_interruptors
python -m tutorials.v1.getting_started.06_partial_recovery
python -m tutorials.v1.getting_started.07_liber_primus_source
```

- `04` runs the same request twice with the same seed and compares the results.
- `05` tells RDP which positions are interruptors: symbols the cipher leaves alone.
- `06` gives the search a small budget and looks at the part of the message it
  recovers. Finishing a run does not always mean finding the whole answer.
- `07` loads Welcome Pilgrim from the bundled Liber Primus sources and looks
  at the text and word information available for a search.

## Look at the result, then prepare a real case

```text
python -m tutorials.v1.getting_started.08_reading_a_result
python -m tutorials.v1.getting_started.09_changing_search_budget
python -m tutorials.v1.getting_started.10_prepare_a_real_source_search
```

- `08` shows where to find the candidate, why the run stopped, how much work
  it did and which settings it used. It also checks whether a known answer
  helped the search.
- `09` changes only beam width. Both searches find the same answer here, so
  we can see what the extra work bought us.
- `10` puts together a Welcome Pilgrim request using the existing solved-source
  setup. It stops before `api.run`, so you can inspect and change the request
  before committing to the longer search.

The companion [anatomy of a run](anatomy_of_a_run.md) explains how these objects
fit together and which options you might want to change.

## Run the release selection

```text
python tutorials/v1/run_tutorials.py
```

The default `RELEASE` group contains all ten stops plus columnar
transposition, repeating multiplication and scheduled-stream lookup examples.
The previous seven-stop selection took about 51 seconds on the reference CPU.
The expanded selection has not been timed as a whole; runtime depends on hardware.

To run only the numbered files, edit the runner and set:

```python
RUN_SET = TutorialRunSet.GETTING_STARTED
```

To print each subprocess output in full, set:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

Both settings are near the top of `run_tutorials.py`.

## Read results without flattering them

Check, in roughly this order:

1. recovered text and key;
2. how much of the original was recovered, if you have it for comparison;
3. execution status, stop category and stop reason;
4. the requested and effective seed;
5. scoring and solver configuration;
6. whether a known answer helped set up or stop the search, or was only used
   to check the result afterwards.

The scorer helps us choose which candidates to investigate. We still need to
check whether the best-looking one makes sense for the problem.

Continue with [`runes and text`](runes_and_text.md), then choose a worked case
from the complete [`example catalogue`](../../tutorials/v1/README.md).
