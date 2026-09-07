# Learner glossary

This page defines the words and names used anywhere in the learning track.

You do not need to memorise them. Use this page when a term appears that you do
not recognise.

## Plaintext

The message before encryption.

For example:

```text
WELCOME
```

## Ciphertext

The encrypted message.

In Liber Primus, the ciphertext is written as runes.

## Rune

One symbol from the 29-rune alphabet used by Liber Primus.

## Rune index

RDP performs cipher maths with numbers rather than rune characters.

Each rune is represented by one number from `0` to `28`.

For example:

```text
(4, 17, 2, 28, ...)
```

is a sequence of rune indices.

Those numbers are not another cipher. They are simply the rune symbols written
in a form convenient for arithmetic.

## `ct_idx`

Short for **ciphertext indices**.

This is the ciphertext represented as rune indices.

## Runeglish

RDP uses **Runeglish** for the Latin/English-oriented representation and
language treatment of rune text.

It is used when displaying candidate plaintext and when building language
models for rune-based English.

## Cipher

The rule that relates plaintext, key and ciphertext.

Examples include:

```text
Vigenere
substitution
rail fence
columnar transposition
```

Choosing a cipher in RDP means:

> try this kind of relationship between the unknown plaintext and the observed
> ciphertext.

## `CipherSpec`

The description of the cipher hypothesis used in a run.

For example:

```python
api.CipherSpec.vigenere()
```

means:

> test a Vigenere cipher.

The word `Spec` means specification: it describes what to run rather than being
the live cipher implementation itself.

## Key

The information that controls a cipher.

For a repeating Vigenere cipher, a key might be:

```text
(3, 1, 4)
```

Those values repeat across the text.

## Key length

The number of values in the repeating key.

```text
(3, 1, 4)
```

has key length `3`.

## Key space

The set of keys RDP is allowed to search.

For example:

```python
api.KeySpec.repeating(length=3)
```

means:

> search repeating three-value keys.

It does not say what the key values are.

## `KeySpec`

The description of the allowed key space.

It tells RDP what a valid key looks like.

The key model also determines the legal operations the solver can use when it
changes candidate keys.

## Solver

The search method.

A solver proposes candidate keys, evaluates them and decides which candidates
to keep exploring.

## `SolverSpec`

The description of the solver and its search settings.

For example:

```python
api.SolverSpec.beam_search(...)
```

means:

> use Beam search.

## Beam search

The main solver used in the beginner examples.

Very roughly:

```text
start with several candidate keys
-> make legal variations of the stronger candidates
-> decrypt and score them
-> keep the best few
-> repeat
```

A useful mental model is **guided reshuffling of candidate keys**.

It is not blindly shuffling the whole key space. The key model defines legal
changes, the scorer ranks the resulting plaintexts, and Beam keeps the stronger
candidates for the next round.

## Width

The number of candidate keys Beam keeps alive after each round.

For example:

```python
width=64
```

means Beam keeps the best 64 candidates before continuing.

A larger width explores more alternatives but usually does more work.

## Round

One step of Beam search.

In a round, Beam expands some of the current candidates into nearby alternatives,
scores them, then keeps the best candidates up to the chosen width.

## `rounds=None`

In RDP, `rounds=None` does **not** mean zero search.

It means:

> choose the number of rounds automatically.

The current automatic rule is:

```text
max(2 * key_length, 12)
```

So for a key length of `8`:

```text
rounds=None
```

means:

```text
up to 16 rounds (an earlier stop can end the run)
```

## Seed

A number used to make random choices reproducible.

If a solver uses randomness, the same seed helps another person repeat the same
search choices.

A seed is not part of the cipher or the key.

It controls the solver's random stream.

## Search budget

The amount of work allowed for a search.

Width, rounds, generations, iterations and similar settings can all contribute
to the search budget.

More budget can explore more candidates, but it does not make a wrong cipher
hypothesis become correct.

## Candidate

One possible answer being considered by the solver.

A candidate usually means a candidate key and the plaintext produced by that
key.

## Evaluation

The process of taking a candidate key, decrypting the ciphertext and assigning
the resulting plaintext a score.

## Score

A number used to rank candidate plaintexts.

Higher is better under the requested scoring model.

A high score is evidence that one candidate looks more language-like than
another. It is not proof that the decryption is correct.

See [What can the score tell you?](05_scoring_limits.md).

## Scorer

The part of RDP that assigns scores to candidate plaintexts.

The solver chooses what to try next.

The scorer judges the candidate produced by that choice.

## Language model

Statistical information about what Runeglish tends to look like.

RDP can use rune patterns and word-length information to decide whether one
candidate looks more language-like than another.

## N-gram

A sequence of `n` neighbouring items.

For example:

```text
unigram  = one rune
bigram   = two neighbouring runes
trigram  = three neighbouring runes
```

RDP language models can use n-gram evidence when scoring plaintext.

## WLI

WLI means **word-length information**.

It records where each rune sits inside a word and how long that word is.

For a five-rune word, the entries could look like:

```text
(0, 5)
(1, 5)
(2, 5)
(3, 5)
(4, 5)
```

You do not need to construct WLI by hand in the beginner examples.

## Source

A named piece of input text.

For Liber Primus, RDP can load reviewed source material by label rather than
requiring you to copy rune strings manually.

## Source label

A stable name used to identify a reviewed source.

For example:

```text
welcome_pilgrim
```

identifies the Welcome Pilgrim source.

## `payload`

An internal term for data passed between parts of the program. It also appears
in ordinary phrases such as a JSON payload.

For Liber Primus data in the public API, use:

```python
source_data = api.liber_primus.load_source("welcome_pilgrim")
```

This returns `SourceData`. `api.liber_primus.source(...)` creates a source
reference for a run instead of loading the data immediately.

## `RuneIndexInput`

A typed input containing rune indices, optionally with WLI. It can hold
ciphertext for a run or a plaintext candidate for scoring.

It is precise, but most beginners should not need to construct one when using a
named Liber Primus source.

## Problem input

The ciphertext and associated information supplied to a run.

It can be raw rune text, rune indices, or a named source reference.

## `RunSpec`

The description of one complete experiment.

It combines:

```text
problem input
cipher
key space
solver
scoring
```

and other optional settings.

## Run

One complete cryptanalytic experiment.

A run starts from the requested input and settings, searches candidate keys, and
returns the best result found plus evidence about how the search behaved.

## `api.run(...)`

The ordinary function that executes a `RunSpec`.

## Result

The object returned by a completed run.

It contains the best candidate plus reports and reproducibility information.

## Plaintext representations

`plaintext_indices`, `plaintext_runes` and `plaintext_rune_latin` are three
views of the same candidate. RuneLatin uses `|` between rune tokens, so the LTR
encoding `TH|E` and RTL encoding `T|H|E` remain visibly different. Both are
valid for the direction-specific rune sequence. `word_length_information`
carries the known word boundaries. None of these fields is an English
translation.

## `key`

The candidate key that produced the best returned plaintext.

## `score`

The score assigned to the best returned candidate.

## Stop reason

The recorded reason the search ended.

Examples include reaching a budget, hitting a target, or stopping after a
plateau.

## Evaluation count

The number of candidate evaluations performed by the solver.

It is one useful measure of how much search work occurred.

## Plateau

A period during which the best score is no longer improving enough.

Some solvers can stop after a sufficiently long plateau rather than continuing
to spend search budget without progress.

## Interruptor

A position in the ciphertext that is treated specially rather than being
processed by the ordinary repeating cipher stream.

Interruptors appear in some Liber Primus solving hypotheses.

They are not needed for the first learning examples.

## Reproducible

A run is reproducible when another person has enough information to repeat the
same experiment and understand what was changed.

That includes the source, cipher, key model, solver settings, scoring settings
and any randomness that affects the search.

Next: [Apply a known key](01_apply_a_known_key.md).

## Default

The setting RDP uses when you omit an optional argument.

## CPU

The computer's general-purpose processor. Ordinary beginner runs use it.

## Restart

Another search start within the same configured run. It consumes the next
choices from that run's random-number stream.

## Target score

A chosen score at which to stop early. Reaching it is not proof of a decryption.

## Transcript version

The identity of the exact stored Liber Primus transcription used by a source.
A source reference preserves it so a different transcription is not substituted
silently when the request is reused.

## Source reference

A typed description of named source data, including its identity and version.
`api.liber_primus.source("welcome_pilgrim")` produces one for a run.

## Runtime

The software and computing environment that executes the described run.

## Materialise

Resolve a run description into the data and components needed to execute it.

## `RawTextInput`

A run input containing text. RDP converts the text to rune indices and derives
word boundaries when spaces are present.

## API

Application programming interface: the functions and types your Python script
uses to ask RDP to do work. `from rdp import api` imports that interface.

## Python

The programming language used for these examples. A script is a file of Python
instructions; `print(...)` shows a value in the terminal.

## Tuple

An ordered, fixed collection of values, such as the key `(3, 1, 4)`. `(3,)` is
a tuple with one value; its comma matters in Python.

## Wheel

An installable Python package file. RDP's wheel includes the native components,
the small default language models and the active LP transcript.

## Cipher hypothesis

An assumption about how the ciphertext was produced. A completed search tests
that assumption with particular settings; it does not prove the assumption.

## Population

The collection of candidate keys currently being explored.

## `None`

Python's value for an omitted or absent setting. Its effect depends on the
setting: for Beam's seed, RDP records requested `None` and effective `0`.
