# Learner glossary

This page defines the words and names used anywhere in the learning track.

You do not need to memorise them. Use this page when a term appears that you do
not recognise.

## English

Ordinary natural-language English.

RDP keeps this name for the language itself. It does not use **English** to
mean rune glyphs or Latin letters standing for rune tokens.

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

## Rune text

Actual rune glyphs, such as:

```text
ᚦᛖ ᛚᚩᛋᛋ
```

Spaces can preserve known word boundaries.

## RuneLatin

A Latin rendering of rune tokens. Rune boundaries are kept explicit with `·`
and spaces separate words:

```text
TH·E L·O·S·S
```

RuneLatin is a rune representation, not an English translation. The exact
rune tokens depend on the encoded indices.

## Reading-direction RuneLatin

A presentation view that keeps rune boundaries visible while making RTL text
read naturally to a person.

For RTL `READ`, the canonical rune identities are:

```text
R·AE·D
```

while the reading-direction form is:

```text
R·EA·D
```

The middle dot still marks one rune boundary. Use canonical RuneLatin when exact
rune identity must round-trip; use the reading form for display.

## Text direction

The direction used when English is encoded into runes and when direction-aware
text is presented.

`LTR` means **left to right**. `RTL` means **right to left**. RDP defaults to
`LTR`. `TextDirection` is the public enum used to select them. Text direction is
part of the run or standalone scoring request; it is not a different cipher.

## Runeglish

English represented and analysed through the 29-rune system.

RDP uses Runeglish when tokenising English into runes and when building or
applying language evidence for rune-based English. It is not another name for
RuneLatin. Conversion from English is not lossless because different English
spellings can produce the same rune sequence.

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

`RuneIndices` is the public type name for an ordered sequence of rune-index
values.

## Rune prime

The prime number corresponding to a rune when gematria arithmetic requires
prime values. Rune primes are derived from rune indices; they are not a
different alphabet.

## `ct_idx`

Short for **ciphertext indices**.

This is the ciphertext represented as rune indices.

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

## Concrete key / `ConcreteKey`

The actual key values used to encrypt, decrypt or evaluate one candidate.

For example, `(3, 1, 4)` is a concrete key. `KeySpec.repeating(length=3)` is not:
it describes the keys that may be searched without choosing their values.

## KeyOps

The runtime operations that define legal changes to a particular key model.
Solvers use KeyOps to mutate, expand or combine candidate keys without having to
know the details of every key shape.

Most users choose a `KeySpec`; they do not construct KeyOps directly.

## Initial key / `InitialKeys`

A concrete key supplied as a starting point for a search. It can guide where the
solver begins without changing which keys the key space allows. `InitialKeys` is
the public type used when one or more starting keys are supplied.

## Repeating key

A key whose values repeat across the text, such as `(3, 1, 4, 3, 1, 4, ...)`.

## Structured key

A key with meaningful parts rather than one undifferentiated sequence. The
cipher and key model define what those parts mean.

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

Width, rounds, generations, iterations, steps and similar settings can all
contribute to the search budget.

More budget can explore more candidates, but it does not make a wrong cipher
hypothesis become correct.

## Generation

One update of a population-based solver such as a genetic algorithm.

## Iteration

One repeated update in a solver whose budget is expressed in iterations. Its
exact work depends on that solver.

## Step

One unit in a solver that exposes a `steps` budget. A step is solver-specific; it
is not a universal RDP measure of work.

## Start

One starting point for a search. Some methods can try several starts or
restarts. These terms describe search behaviour, not separate runs unless the
solver says otherwise.

## Work unit

A generic phrase for solver effort, not a single V1 field. Beam rounds, genetic
algorithm generations, simulated-annealing iterations and other solver budgets
are intentionally reported in their own terms rather than converted into one
misleading universal number.

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

## `ScoringConfig`

The public configuration object that selects scoring lanes, language-model
orders, objective, backend and specialist scoring options. It describes scoring
behaviour; it does not itself score a candidate.

## `api.score(...)` and `api.score_many(...)`

Public operations for scoring plaintext candidates directly, without building a
cipher, key space or solver.

`score(...)` returns one value. `score_many(...)` returns one value per candidate
in the same order. They use the same `RuneInput`, scoring, direction and compute
device contracts as normal runs.

## Objective

The rule that selects the scalar value the scorer optimises or returns. For
example, RDP can use a percentile of language-model log probability.

## Metric

A general measured quantity used to compare or describe results. In RDP, a
metric is not automatically the solver's selected score.

## Statistic

A particular summary calculated from scoring evidence, such as log probability,
a z-score sum or a median-absolute-deviation sum.

## Character lane

The scoring lane that uses neighbouring rune identities without requiring word
boundaries.

## WLI lane

The scoring lane that uses word-length information. It requires meaningful WLI
when it has effective scoring weight.

## Raw score

A score before a later calibration or conversion, such as conversion to a
percentile. Raw scores may have a scale that is useful only within the scorer
that produced them.

## Percentile

A calibrated position within a reference score distribution. A percentile is a
ranking statistic, not a probability that the plaintext is correct.

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
It is metadata aligned with rune indices, not another rendering of the
plaintext.

For a five-rune word, the entries could look like:

```text
(0, 5)
(1, 5)
(2, 5)
(3, 5)
(4, 5)
```

You do not need to construct WLI by hand in the beginner examples.

## `WordLengthPolicy`

The run setting that controls how missing word-length information is handled.
The V1 default is `INFER` where the input representation provides enough
information to infer word boundaries.

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

## Source reference / `SourceReferenceInput`

A typed description of named source data. It records the source kind, asset ID,
asset version and resolver-owned reference information without embedding a local
file path.

`api.liber_primus.source("welcome_pilgrim")` creates one for a run.

## Source resolver

The code that turns a `SourceReferenceInput` into the actual rune indices and
word-length information at run time. The resolver also checks the recorded
source identity and version.

## `load_source(...)`

A direct LP data-inspection operation. `api.liber_primus.load_source(label)`
returns the loaded `SourceData`; `api.liber_primus.source(label)` returns a
reference for a run instead.

## `SourceData`

The loaded Liber Primus data returned by `load_source(...)` and related direct
inspection helpers. It contains numeric ciphertext indices, WLI and source
metadata; it is data, not a `RunSpec.problem_input` reference.

## `payload`

An internal term for data passed between parts of the program. It also appears
in ordinary phrases such as a JSON payload.

For Liber Primus data in the public API, use:

```python
source_data = api.liber_primus.load_source("welcome_pilgrim")
```

This returns `SourceData`. `api.liber_primus.source(...)` creates a source
reference for a run instead of loading the data immediately.

## `RuneInput`

A typed rune input containing rune indices, rune glyphs, RuneLatin, or English.
It is used by runs and by standalone scoring. Index input can include WLI; text
input derives word boundaries from spaces.

It is precise, but most beginners should not need to construct one when using a
named Liber Primus source.

## `RuneInputFormat`

The explicit representation attached to a `RuneInput` when inference is not
wanted or would be ambiguous:

```text
INDICES
RUNES
RUNE_LATIN
ENGLISH
```

## Problem input / `ProblemInput`

The ciphertext and associated information supplied to a run. `ProblemInput` is
the public type alias covering the accepted input objects.

It can be a `RuneInput` or a named source reference.

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

## Text permutation

An optional reordering of input positions applied as part of a run request. It
is explicit experiment configuration, not an automatic text-direction change.

## Run

One complete cryptanalytic experiment.

A run starts from the requested input and settings, searches candidate keys, and
returns the best result found plus evidence about how the search behaved.

## `api.run(...)`

The ordinary function that executes a `RunSpec`.

## Result / `RunResult`

The object returned by a completed run.

It contains the best candidate plus reports and reproducibility information.

## `SolverReport`

Structured evidence about the search itself: the best key, stopping information,
search accounting and other solver-owned observations.

## `ScorerReport`

Structured evidence about scoring: the selected objective, effective scorer
configuration and scoring capability information. It is different from
`RunResult.score`, which is the convenient scalar value for the selected
candidate.

## Plaintext representations

`plaintext_indices`, `plaintext_runes`, `plaintext_rune_latin`, and
`plaintext_reading_rune_latin` are views of the same candidate. Canonical
`plaintext_rune_latin` uses the exact label of every rune, with `·` between
tokens. The reading field applies direction-aware presentation: RTL “READ” is
canonical `R·AE·D` but reading-order `R·EA·D`. Use the canonical form when rune
identity must round-trip. `word_length_information` carries the known word
boundaries. None of these fields is an English translation.

## `key`

The candidate key that produced the best returned plaintext.

## `score`

The score assigned to the best returned candidate.

## Status / `RunStatus`

The structured outcome of a run. `RunStatus` separates whether execution
completed from why the search stopped and, where applicable, whether recovery
was established.

## Stop reason

The recorded reason the search ended.

Examples include reaching a budget, hitting a target, or stopping after a
plateau.

## Stop category

A broader grouping of stop reasons, such as a budget or target condition. Use
the exact stop reason when the detailed cause matters.

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
`InterruptorConfig` is the public run configuration for exact or searched
interruptor behaviour.

They are not needed for the first learning examples.

## Reproducible / reproducibility

A run is reproducible when another person has enough information to repeat the
same experiment and understand what was changed.

That includes the source, cipher, key model, solver settings, scoring settings
and any randomness that affects the search. `RunResult.reproducibility` records
replay-relevant metadata.

## Telemetry

Execution observations collected during a run, such as solver progress, timing,
device information and scorer activity. Telemetry observes the run; it should
not change candidate ranking.

## Oracle

RDP's structured known-answer comparison. Oracle information may be used only
after a search to measure recovery, or deliberately as part of a diagnostic
method. Those two uses support different claims.

## Known answer / reference

Truth already known for a solved or test problem, such as an expected plaintext
or key. A reference can be useful for checking a result, but using it to rank or
select candidates makes the experiment reference-guided rather than independent
recovery.

## Artifact

A file produced or retained as part of a run, such as a configuration, report,
log or saved result. `RunResult.artifacts` records known run artifacts without
turning every in-memory result into a file.

## Logging / `LoggingConfig`

Logging is the optional file-output side of a run. `LoggingConfig` selects the
durable output behaviour. A normal `RunResult` exists in memory whether or not
logging is enabled.

Next: [Apply a known key](01_apply_a_known_key.md).

## Default

The setting RDP uses when you omit an optional argument.

## CPU

The computer's general-purpose processor. Ordinary beginner runs use it.

## Compute device / `ComputeDevice`

The processor family requested for execution. `ComputeDevice.CPU` is the V1
default; `ComputeDevice.CUDA` requests supported NVIDIA GPU execution.

## CUDA

NVIDIA's GPU compute platform. CUDA changes where supported numerical work runs;
it is an execution choice, not additional cryptanalytic evidence.

## Asset

A data file or packaged resource used by RDP, such as a language model,
calibration table or Liber Primus transcript.

## Asset profile

A named set of assets expected for a particular installation or validation job.
For example, the full V1 profile includes the complete supported language-model
set.

## CI-light

The smaller asset/test profile used for routine continuous-integration checks.
It is designed to catch ordinary regressions without downloading or running the
complete release asset set.

## Full V1 assets

The complete supported V1 asset profile used for full scoring/examples and
release-level validation. It is broader than CI-light.

## Restart

Another search start within the same configured run. It consumes the next
choices from that run's random-number stream.

## Target score

A chosen score at which to stop early. Reaching it is not proof of a decryption.

## Transcript version

The identity of the exact stored Liber Primus transcription used by a source.
A source reference preserves it so a different transcription is not substituted
silently when the request is reused.

## Runtime

The software and computing environment that executes the described run.

## Materialise

Resolve a run description into the data and components needed to execute it.

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
