# Word and crib dictionaries

Load short-word dictionaries for text constraints and related workflows.

## Where to look

- [loaders.py](loaders.py) — Load direction-specific CSV words or raw unigram wordlists.
- [words_1_2_3.py](words_1_2_3.py) — Bundled short-word definitions.
- [cribs/](cribs/) — Retained reference crib material.

## Choices and extension

Word length and direction determine the appropriate dictionary. Distinguish a supplied crib, which constrains a problem, from a language-model score used to rank candidates. Dictionary provenance matters when assessing how much prior knowledge a solve used.

Continue with the [guide](../../../../docs/guides/runes_and_text.md) or the [package map](../../README.md).
