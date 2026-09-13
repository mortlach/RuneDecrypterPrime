# Words used in RDP

If you are new to RDP, start here.

This is the short glossary for the learning track: the words you need to follow
the beginner examples without having to learn the whole API vocabulary at once.

You do not need to memorise any of it. Come back when a term is unfamiliar.

**Jump to:** [text and runes](#text-and-runes) · [ciphers and keys](#ciphers-and-keys) ·
[searching](#searching) · [scoring](#scoring) · [runs and results](#runs-and-results) ·
[Liber Primus sources](#liber-primus-sources)

For the complete RDP vocabulary, including API types, reports, scoring details,
runtime terms and installation language, see the
[full A-Z glossary](../reference/glossary.md).

## Text and runes

### English

Ordinary natural-language English.

RDP keeps this name for the language itself. It does not use **English** to mean
rune glyphs or Latin letters standing for rune tokens.

### Plaintext

The message before encryption.

```text
WELCOME
```

### Ciphertext

The encrypted message.

In Liber Primus, the ciphertext is written as runes.

### Rune

One symbol from the 29-rune alphabet used by Liber Primus.

### Rune text

Actual rune glyphs, such as:

```text
ᚦᛖ ᛚᚩᛋᛋ
```

Spaces can preserve known word boundaries.

### RuneLatin

A Latin rendering of rune tokens. Rune boundaries are kept explicit with `·`
and spaces separate words:

```text
TH·E L·O·S·S
```

RuneLatin is a rune representation, not an English translation.

### Reading-direction RuneLatin

A presentation view that keeps rune boundaries visible while making RTL text
read naturally to a person.

For RTL `READ`, canonical RuneLatin is:

```text
R·AE·D
```

while the reading-direction form is:

```text
R·EA·D
```

Use canonical RuneLatin when exact rune identity must round-trip; use the
reading form for display.

### Runeglish

English represented and analysed through the 29-rune system.

RDP uses Runeglish when turning English into runes and when applying language
evidence to rune-based English. It is not another name for RuneLatin.

### Rune index

RDP performs cipher maths with numbers rather than rune characters.

Each rune is represented by one number from `0` to `28`. A sequence such as:

```text
(4, 17, 2, 28, ...)
```

is a sequence of rune indices.

### Text direction

The direction used when English is encoded into runes and when direction-aware
text is presented.

`LTR` means **left to right** and `RTL` means **right to left**. RDP defaults to
`LTR`.

## Ciphers and keys

### Cipher

The rule that relates plaintext, key and ciphertext.

Examples include Vigenere, substitution, rail fence and columnar transposition.

Choosing a cipher in RDP means:

> try this kind of relationship between the unknown plaintext and the observed
> ciphertext.

### Cipher hypothesis

An assumption about how the ciphertext was produced.

A successful search is evidence for that hypothesis under the tested settings;
it does not by itself prove the hypothesis.

### `CipherSpec`

The public description of the cipher hypothesis used in a run.

```python
api.CipherSpec.vigenere()
```

`Spec` means specification: it describes what to run rather than being the live
cipher implementation.

### Key

The information that controls a cipher.

For a repeating Vigenere cipher, a key might be:

```text
(3, 1, 4)
```

### Key length

The number of values in a repeating key.

`(3, 1, 4)` has key length `3`.

### Key space

The set of keys RDP is allowed to search.

```python
api.KeySpec.repeating(length=3)
```

means:

> search repeating three-value keys.

It does not say what the values are.

### `KeySpec`

The public description of the allowed key space. It tells RDP what a valid key
looks like and determines the legal changes a solver can make.

### Repeating key

A key whose values repeat across the text:

```text
3, 1, 4, 3, 1, 4, ...
```

### Interruptor

A ciphertext position treated specially instead of being processed by the
ordinary repeating cipher stream.

Interruptors appear in some Liber Primus solving hypotheses.

## Searching

### Solver

The search method.

A solver proposes candidate keys, evaluates them and decides which candidates
to keep exploring.

### `SolverSpec`

The public description of the solver and its search settings.

```python
api.SolverSpec.beam_search(...)
```

### Beam search

The main search method used in the beginner examples.

Very roughly:

```text
start with several candidate keys
-> make legal variations
-> decrypt and score them
-> keep the strongest few
-> repeat
```

A useful mental model is **guided reshuffling of candidate keys**.

### Candidate

One possible answer being considered by the solver.

Usually this means a candidate key and the plaintext produced by it.

### Width

The number of candidate keys Beam keeps alive after each round.

A larger width explores more alternatives but usually does more work.

### Round

One Beam-search update: expand candidates, score them, then keep the best ones.

### Seed

A number used to make random search choices reproducible.

A seed is not part of the cipher or the key.

### Search budget

The amount of work allowed for a search.

Width, rounds, generations, iterations and similar settings can all contribute
to the budget.

More budget can explore more candidates. It cannot make the wrong cipher
hypothesis become correct.

### Plateau

A period during which the best score is no longer improving enough.

Some solvers can stop after a sufficiently long plateau.

## Scoring

### Score

A number used to rank candidate plaintexts.

Higher is better under the requested scoring model.

A high score is evidence that one candidate looks more language-like than
another. It is not proof that the decryption is correct.

See [What can the score tell you?](05_scoring_limits.md).

### Scorer

The part of RDP that assigns scores to candidate plaintexts.

The solver chooses what to try. The scorer judges what that choice produced.

### Language model

Statistical information about what Runeglish tends to look like.

RDP can use rune patterns and word-length information to decide whether one
candidate looks more language-like than another.

### WLI

WLI means **word-length information**.

It records where each rune sits inside a word and how long that word is. It is
metadata aligned with rune indices, not another rendering of the plaintext.

You do not need to construct WLI by hand in the beginner examples.

## Runs and results

### RunSpec

The description of one complete experiment.

It combines the problem input, cipher, key space, solver, scoring and other
optional settings.

### Run

One complete cryptanalytic experiment.

A run starts from the requested input and settings, searches candidate keys and
returns the best result found plus evidence about how the search behaved.

### Result / RunResult

The object returned by a completed run.

It contains the best candidate plus reports and reproducibility information.

### Stop reason

The recorded reason the search ended.

Examples include reaching a budget, hitting a target or stopping after a
plateau.

### Known answer / reference

Truth already known for a solved or test problem, such as an expected plaintext
or key.

A reference is useful for checking a result afterwards. Using it to rank or
select candidates makes the experiment reference-guided rather than independent
recovery.

## Liber Primus sources

### Source

A named piece of input text.

For Liber Primus, RDP can load reviewed source material by label rather than
requiring you to copy rune strings manually.

### Source label

A stable name used to identify a reviewed source.

```text
welcome_pilgrim
```

identifies the Welcome Pilgrim source.

### `api.liber_primus.source(...)`

Creates a source reference for a run.

```python
source = api.liber_primus.source("welcome_pilgrim")
```

The source is resolved when the run executes.

### `api.liber_primus.load_source(...)`

Loads the source data directly so you can inspect its ciphertext indices, WLI
and metadata.

### `api.liber_primus.load_plaintext(...)`

Loads the known solved plaintext reference for an LP source when one is
available.

It is reference data. It is not automatically supplied to the solver.

---

Need something not listed here? Use the
[full A-Z glossary](../reference/glossary.md).

Next: [Apply a known key](01_apply_a_known_key.md).
