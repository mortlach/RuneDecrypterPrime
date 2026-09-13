# RDP glossary

This is the full reference glossary for RDP terminology.

If you are new to the project, the shorter
[beginner glossary](../learn/00_words_used_here.md) is usually the better place
to start. This page is for looking up the exact term you have run into.

**Jump to:**
[A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) ·
[G](#g) · [H](#h) · [I](#i) · [J](#j) · [K](#k) · [L](#l) ·
[M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) · [R](#r) ·
[S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w) · [X](#x) ·
[Y](#y) · [Z](#z)

The definitions below are reference material, not a reading order.

## A

### API

Application programming interface: the functions and types your Python script
uses to ask RDP to do work.

```python
from rdp import api
```

imports the public interface.

### `api.run(...)`

The ordinary public function that executes a `RunSpec`.

### `api.score(...)` and `api.score_many(...)`

Public operations for scoring plaintext candidates directly without building a
cipher, key space or solver.

`score(...)` returns one value. `score_many(...)` returns one value per
candidate in the same order. They use the same `RuneInput`, scoring, direction
and compute-device contracts as normal runs.

### Artifact

A file produced or retained as part of a run, such as a configuration, report,
log or saved result.

With logging enabled, `RunResult.artifacts` records agreement-backed files
actually present. It is empty for an in-memory-only run.

### Asset

A data file or packaged resource used by RDP, such as a language model,
calibration table or Liber Primus transcript.

### Asset profile

A named set of assets expected for a particular installation or validation job.

The full V1 profile includes the complete supported language-model set.

## B

### Beam search

A search method that keeps a limited number of the strongest candidates after
each round.

Very roughly:

```text
start with candidate keys
-> make legal variations
-> decrypt and score them
-> keep the best few
-> repeat
```

The key model defines legal changes, the scorer ranks the resulting plaintexts,
and Beam keeps the stronger candidates for the next round.

## C

### Candidate

One possible answer being considered by the solver.

A candidate usually means a candidate key and the plaintext produced by that
key.

### Character lane

The scoring lane that uses neighbouring rune identities without requiring word
boundaries.

### Cipher

The rule that relates plaintext, key and ciphertext.

Examples include Vigenere, substitution, rail fence and columnar transposition.

### Cipher hypothesis

An assumption about how the ciphertext was produced.

A completed search tests that assumption with particular settings; it does not
prove the assumption.

### `CipherSpec`

The public description of the cipher hypothesis used in a run.

```python
api.CipherSpec.vigenere()
```

means: test a Vigenere cipher.

`Spec` means specification: it describes what to run rather than being the live
cipher implementation itself.

### Ciphertext

The encrypted message.

In Liber Primus, the ciphertext is written as runes.

### `ct_idx`

Short for **ciphertext indices**: ciphertext represented as rune indices.

### CI-light

The smaller asset/test profile used for routine continuous-integration checks.

It catches ordinary regressions without downloading or running the complete
release asset set.

### Compute device / `ComputeDevice`

The processor family requested for execution.

`ComputeDevice.CPU` is the V1 default. `ComputeDevice.CUDA` requests supported
NVIDIA GPU execution.

### Concrete key / `ConcreteKey`

The actual key values used to encrypt, decrypt or evaluate one candidate.

`(3, 1, 4)` is a concrete key. `KeySpec.repeating(length=3)` is not: that
describes a set of keys.

### CPU

The computer's general-purpose processor. Ordinary beginner runs use it.

### CUDA

NVIDIA's GPU compute platform.

CUDA changes where supported numerical work runs; it is an execution choice,
not additional cryptanalytic evidence.

## D

### Default

The setting RDP uses when you omit an optional argument.

## E

### English

Ordinary natural-language English.

RDP does not use **English** to mean rune glyphs or Latin letters standing for
rune tokens.

### Evaluation

Taking a candidate key, decrypting the ciphertext and assigning the resulting
plaintext a score.

### Evaluation count

The number of candidate evaluations performed by the solver.

It is one useful measure of search work.

## F

### Full V1 assets

The complete supported V1 asset profile used for full scoring, examples and
release-level validation.

It is broader than CI-light.

## G

### Generation

One update of a population-based solver such as a genetic algorithm.

## H

No current glossary entries.

## I

### Initial key / `InitialKeys`

A concrete key supplied as a starting point for a search.

It can guide where the solver begins without changing which keys the key space
allows.

### Interruptor

A position in the ciphertext that is treated specially rather than being
processed by the ordinary repeating cipher stream.

`InterruptorConfig` is the public run configuration for exact or searched
interruptor behaviour.

### Iteration

One repeated update in a solver whose budget is expressed in iterations.

Its exact work depends on that solver.

## J

No current glossary entries.

## K

### Key

The information that controls a cipher.

For a repeating Vigenere cipher, a key might be:

```text
(3, 1, 4)
```

### `key`

The candidate key that produced the best returned plaintext.

### Key length

The number of values in a repeating key.

`(3, 1, 4)` has key length `3`.

### Key space

The set of keys RDP is allowed to search.

```python
api.KeySpec.repeating(length=3)
```

means: search repeating three-value keys.

It does not say what the values are.

### KeyOps

Runtime operations that define legal changes to a particular key model.

Solvers use KeyOps to mutate, expand or combine candidate keys without having to
know the details of every key shape.

Most users choose a `KeySpec`; they do not construct KeyOps directly.

### `KeySpec`

The public description of the allowed key space.

It tells RDP what a valid key looks like and determines the legal operations the
solver can use when it changes candidate keys.

### Known answer / reference

Truth already known for a solved or test problem, such as an expected plaintext
or key.

Using it only after a run is ordinary verification. Using it to rank or select
candidates makes the experiment reference-guided.

## L

### Language model

Statistical information about what Runeglish tends to look like.

RDP can use rune patterns and word-length information to decide whether one
candidate looks more language-like than another.

### `load_source(...)`

A direct LP data-inspection operation.

`api.liber_primus.load_source(label)` returns loaded `SourceData`;
`api.liber_primus.source(label)` returns a reference for a run.

### `load_plaintext(...)`

`api.liber_primus.load_plaintext(label)` returns known solved LP plaintext
reference data when available.

It is separate from ciphertext source data and is not automatically supplied to
`api.run()`.

### Logging / `LoggingConfig`

The optional file-output side of a run.

`LoggingConfig` selects durable output behaviour. A normal `RunResult` exists in
memory whether or not logging is enabled.

## M

### Materialise

Resolve a run description into the data and components needed to execute it.

### Metric

A general measured quantity used to compare or describe results.

A metric is not automatically the solver's selected score.

## N

### N-gram

A sequence of `n` neighbouring items.

```text
unigram  = one rune
bigram   = two neighbouring runes
trigram  = three neighbouring runes
```

RDP language models can use n-gram evidence when scoring plaintext.

### `None`

Python's value for an omitted or absent setting.

Its effect depends on the setting. For Beam's seed, RDP records requested
`None` and effective `0`.

## O

### Objective

The rule that selects the scalar value the scorer optimises or returns.

For example, RDP can use a percentile of language-model log probability.

### Oracle

RDP's structured report of known-answer use.

Ordinary `api.run()` has no general oracle input, so this report is normally
unavailable. The explicit internal test-key fast path is reported as test-mode
oracle use. External post-run comparison remains the caller's responsibility.

## P

### `payload`

An internal term for data passed between parts of the program.

For Liber Primus data in the public API, prefer `load_source(...)` and
`SourceData`.

### Percentile

A calibrated position within a reference score distribution.

A percentile is a ranking statistic, not a probability that the plaintext is
correct.

### Plaintext

The message before encryption.

### Plaintext representations

`plaintext_indices`, `plaintext_runes`, `plaintext_rune_latin`, and
`plaintext_reading_rune_latin` are views of the same candidate.

Canonical `plaintext_rune_latin` keeps exact rune identity with `·` between
tokens. The reading field is direction-aware presentation.
`word_length_information` carries word boundaries. None of these fields is an
English translation.

### Plateau

A period during which the best score is no longer improving enough.

Some solvers can stop after a sufficiently long plateau instead of continuing
to spend search budget without progress.

### Population

The collection of candidate keys currently being explored.

### Problem input / `ProblemInput`

The ciphertext and associated information supplied to a run.

`ProblemInput` is the public type alias covering accepted input objects,
including `RuneInput` and named source references.

### Python

The programming language used for the examples.

`print(...)` shows a value in the terminal.

## Q

No current glossary entries.

## R

### Raw score

A score before a later calibration or conversion, such as conversion to a
percentile.

Raw-score scales may only be meaningful within the scorer that produced them.

### Reading-direction RuneLatin

A presentation view that keeps rune boundaries visible while making RTL text
read naturally to a person.

For RTL `READ`, canonical RuneLatin is `R·AE·D`; the reading-direction form is
`R·EA·D`.

Use canonical RuneLatin when exact rune identity must round-trip.

### Repeating key

A key whose values repeat across the text, such as:

```text
3, 1, 4, 3, 1, 4, ...
```

### Reproducible / reproducibility

A run is reproducible when another person has enough information to repeat the
same experiment and understand what changed.

That includes source, cipher, key model, solver settings, scoring settings and
randomness that affects the search. `RunSpec` is the complete request;
`RunResult.reproducibility` records the replay metadata owned by the result
rather than copying every request field.

### Restart

Another search start within the same configured run.

It consumes the next choices from that run's random-number stream.

### Result / `RunResult`

The object returned by a completed run.

It contains the best candidate plus reports and reproducibility information.

### Round

One Beam-search update.

Beam expands current candidates into nearby alternatives, scores them and keeps
the best candidates up to the configured width.

### `rounds=None`

For Beam search, `rounds=None` means choose the round budget automatically, not
zero search.

The current automatic rule is:

```text
max(2 * key_length, 12)
```

An earlier stop can still end the run.

### Run

One complete cryptanalytic experiment.

A run starts from requested input and settings, searches candidate keys and
returns the best result plus evidence about how the search behaved.

### Rune

One symbol from the 29-rune alphabet used by Liber Primus.

### Rune index

A numeric representation of a rune used for cipher arithmetic.

Each rune has an index from `0` to `28`.

For example, `(4, 17, 2, 28, ...)` is a sequence of rune indices. Those
numbers are not another cipher; they are the rune symbols written in a form
convenient for arithmetic.

`RuneIndices` is the public type name for an ordered sequence of rune-index
values.

### `RuneInput`

A typed rune input containing rune indices, rune glyphs, RuneLatin or English.

It is used by runs and standalone scoring. Index input can include WLI; text
input derives word boundaries from spaces.

### `RuneInputFormat`

The explicit representation attached to a `RuneInput` when inference is not
wanted or would be ambiguous:

```text
INDICES
RUNES
RUNE_LATIN
ENGLISH
```

### Rune prime

The prime number corresponding to a rune when gematria arithmetic requires
prime values.

Rune primes are derived from rune indices; they are not a different alphabet.

### Rune text

Actual rune glyphs.

Spaces can preserve known word boundaries.

### Runeglish

English represented and analysed through the 29-rune system.

RDP uses Runeglish when tokenising English into runes and when applying language
evidence for rune-based English. It is not another name for RuneLatin.
Conversion from English is not lossless because different English spellings can
produce the same rune sequence.

### RuneLatin

A Latin rendering of rune tokens.

Rune boundaries are kept explicit with `·` and spaces separate words:

```text
TH·E L·O·S·S
```

RuneLatin is a rune representation, not an English translation.

### `RunSpec`

The description of one complete experiment.

It combines problem input, cipher, key space, solver, scoring and other optional
settings.

### Runtime

The software and computing environment that executes the described run.

### Status / `RunStatus`

The structured outcome of a run.

`RunStatus` separates whether execution completed from why the search stopped
and, where applicable, whether recovery was established.

## S

### Score

A number used to rank candidate plaintexts.

Higher is better under the requested scoring model. A high score is evidence,
not proof that the decryption is correct.

### `score`

The score assigned to the best returned candidate.

### Scorer

The part of RDP that assigns scores to candidate plaintexts.

The solver chooses what to try next. The scorer judges the resulting plaintext.

### `ScorerReport`

Structured evidence about scoring: selected objective, primary and raw scores,
typed runtime capability state and scorer-specific telemetry.

Whole-run telemetry stays on `RunResult`. `ScorerReport.score` agrees with
`RunResult.score`; `raw_score` is separate diagnostic evidence when available.

### `ScoringConfig`

The public configuration object that selects scoring lanes, language-model
orders, objective, backend and specialist scoring options.

It describes scoring behaviour; it does not itself score a candidate.

### Search budget

The amount of work allowed for a search.

Width, rounds, generations, iterations, steps and similar settings can all
contribute.

More budget can explore more candidates. It cannot make the wrong cipher
hypothesis correct.

### Seed

A number used to make random choices reproducible.

It controls a solver's random stream; it is not part of the cipher or key.

### Solver

The search method.

A solver proposes candidate keys, evaluates them and decides which candidates
to keep exploring.

### `SolverReport`

Structured evidence about the search itself: best key, stopping information,
search accounting and other solver-owned observations.

### `SolverSpec`

The public description of the solver and its search settings.

```python
api.SolverSpec.beam_search(...)
```

means: use Beam search.

### Source

A named piece of input text.

For Liber Primus, reviewed source material can be loaded by label instead of
copying rune strings manually.

### `SourceData`

Loaded Liber Primus data returned by `load_source(...)` and related inspection
helpers.

It contains numeric ciphertext indices, WLI and source metadata.

### Source label

A stable name used to identify a reviewed source.

`welcome_pilgrim` identifies the Welcome Pilgrim source.

### Source reference / `SourceReferenceInput`

A typed description of named source data.

It records source kind, asset ID, asset version and resolver-owned reference
information without embedding a local file path.

### Source resolver

The code that turns a `SourceReferenceInput` into actual rune indices and
word-length information at run time.

The resolver also checks recorded source identity and version.

### Start

One starting point for a search.

Some methods can try several starts or restarts. These describe search
behaviour, not necessarily separate runs.

### Statistic

A particular summary calculated from scoring evidence, such as log probability,
a z-score sum or a median-absolute-deviation sum.

### Step

One unit in a solver that exposes a `steps` budget.

A step is solver-specific; it is not a universal RDP measure of work.

### Stop category

A broader grouping of stop reasons, such as budget or target condition.

Use the exact stop reason when the detailed cause matters.

### Stop reason

The recorded reason the search ended.

Examples include reaching a budget, hitting a target or stopping after a
plateau.

### Structured key

A key with meaningful parts rather than one undifferentiated sequence.

The cipher and key model define what those parts mean.

## T

### Target score

A chosen score at which to stop early.

Reaching it is not proof of a correct decryption.

### Telemetry

Execution observations collected during a run, such as solver progress, timing,
device information and scorer activity.

Telemetry observes the run; it should not change candidate ranking.

### Text direction

The direction used when English is encoded into runes and when direction-aware
text is presented.

`LTR` means left to right and `RTL` means right to left. RDP defaults to `LTR`.
`TextDirection` is the public enum used to select them. Text direction is part
of the run or standalone scoring request; it is not a different cipher.

### Text permutation

An optional reordering of input positions applied as part of a run request.

It is explicit experiment configuration, not an automatic text-direction
change.

### Transcript version

The identity of the exact stored Liber Primus transcription used by a source.

A source reference preserves it so a different transcription is not silently
substituted when the request is reused.

### Tuple

An ordered, fixed collection of values, such as `(3, 1, 4)`.

`(3,)` is a tuple with one value; its comma matters in Python.

## U

No current glossary entries.

## V

No current glossary entries.

## W

### Wheel

An installable Python package file. RDP's wheel includes the native components,
the small default language models and the active LP transcript.

### Width

The number of candidate keys Beam keeps alive after each round.

A larger width explores more alternatives but usually does more work.

### WLI

WLI means **word-length information**.

It records where each rune sits inside a word and how long that word is. It is
metadata aligned with rune indices, not another rendering of the plaintext.

For a five-rune word the entries could look like:

```text
(0, 5)
(1, 5)
(2, 5)
(3, 5)
(4, 5)
```

### WLI lane

The scoring lane that uses word-length information.

It requires meaningful WLI when it has effective scoring weight.

### `WordLengthPolicy`

The run setting that controls effective word-length information.

The V1 default is `INFER`, which derives or preserves WLI when the input
provides it and leaves it absent otherwise.

`REQUIRE` fails if aligned WLI is unavailable. `DISABLED` removes WLI and
therefore cannot be combined with scoring that requires the WLI lane.

### Work unit

A generic phrase for solver effort, not a single V1 field.

Beam rounds, genetic-algorithm generations, simulated-annealing iterations and
other solver budgets are intentionally reported in their own terms rather than
converted into one misleading universal number.

## X

No current glossary entries.

## Y

No current glossary entries.

## Z

No current glossary entries.
