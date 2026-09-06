# What can the score tell you?


New term? See the [learner glossary](00_words_used_here.md).

RDP uses scoring to rank candidate plaintexts.

That is useful, but a score is not proof that a decryption is correct.

A scorer answers a narrower question:

> under this language model and these scoring settings, which candidate looks
> more like the language we are looking for?

That has several limits.

## Short text gives less evidence

A long candidate contains many rune and word patterns.

A short one may contain only a few.

Two short candidates can therefore receive similar scores even when one happens
to contain a meaningful fragment.

## Plausible nonsense can score well

Language models recognise statistical patterns.

A wrong decryption can accidentally contain common rune pairs, word lengths or
other language-like structure.

The scorer may rank that candidate highly even though the cipher hypothesis is
wrong.

## Unusual correct text can score poorly

A genuine plaintext may contain:

- rare words
- names
- abbreviations
- deliberately strange grammar
- unusual spelling
- text unlike the material used to build the language model

That can make a correct candidate look less ordinary to the scorer.

## Scores depend on the scoring setup

A score is most useful when comparing runs that use the same scoring
configuration.

Changing the language model, direction, n-gram evidence or other scoring
settings can change the numerical scale and ranking.

## What a strong result looks like

A good cryptanalytic result usually has more than a high score.

For example:

```text
a clear plaintext
+
a coherent cipher/key explanation
+
repeatable run settings
+
supporting structure or clues
+
another person can reproduce it
```

RDP helps with the scoring and reproducibility parts.

It does not replace the rest of the argument.

For the full scoring model, see [Scoring](../guides/scoring.md).

Next: [Read the result](05_read_the_result.md).
