# Phase-B filtered n-gram index prototype

Drop these files into the repo, preserving paths:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_filtered_ngram_index_v1.py`
- `tests/tools/benchmarks/periodic_sub_trans/no_wli/analysis/test_build_phaseB_filtered_ngram_index_v1.py`

The script is IDE-friendly. Edit the config block at the top of the script and run `main()`.
There are no command-line arguments.

## What this does

This is not a plain file copier and it does not keep the raw source filename as the output filename.
It builds filtered rune n-gram index files.

Processing order:

1. Read cleaned n-gram rows in the form `word ... word count`.
2. Reject rows that are not plain lowercase English words only.
   This removes `_end_`, quotes, digits, apostrophes, punctuation, and similar marker rows.
3. For each dictionary cut, keep the row only if every word is selected by that cut.
   - `strict` output uses only strict-selected words.
   - `normal` output uses only normal-selected words.
4. Encode kept English phrases into runes in two separate ways:
   - `fwd` uses `Runeglish.encode_english_to_runes(..., direction="ltr")`.
   - `rev` uses `Runeglish.encode_english_to_runes(..., direction="rtl")`.
5. Write four output families:
   - `strict_fwd/`
   - `strict_rev/`
   - `normal_fwd/`
   - `normal_rev/`

Each family gets `ngramN.csv.gz` files, for example `ngram2.csv.gz` or `ngram5.csv.gz`.
The raw source file name is preserved in the `source_file` column and in `raw_ngram_inventory.csv`.

## Five-file local layout

For the five-file local layout, set:

```python
RAW_NGRAM_ROOT = Path("data/scoring/google_ngrams_Version-20200217")
RAW_NGRAM_FILES_BY_ORDER = {
    1: [Path("1grams.txt")],
    2: [Path("2grams.txt")],
    3: [Path("3grams.txt")],
    4: [Path("4grams.txt")],
    5: [Path("5grams.txt")],
}
ENABLED_ORDERS = (2, 3, 4, 5)
```

If the data is later split into folders, leave `RAW_NGRAM_FILES_BY_ORDER` empty and use
`RAW_NGRAM_GLOBS_BY_ORDER` instead.

## Empty-output behaviour

If a file contains only punctuation/end-marker rows, or if no row survives the selected dictionary cut,
the script still writes the expected `ngramN.csv.gz` output with just the CSV header. The summary files record
`dictionary_kept_rows = 0` and `aggregate_rows = 0`. This is intentional: marker-heavy files are transparent to
this no-WLI scorer pass rather than being special-cased or crashing the run.

## Main output columns

The important columns are:

- `rune_key_hex`: deterministic byte key with `0xff` between words.
- `rune_joined`: concatenated rune glyphs without spaces.
- `rune_words`: rune words with word boundaries preserved.
- `rune_lengths`: rune-token length per word.
- `rune_token_ids`: flat rune token IDs.
- `word_token_ids`: rune token IDs split by word.
- `wli`: word-location information for the flat rune token sequence.
- `count`: summed count for duplicate rune keys.
- `phrase_count`: number of Latin phrases collapsed into that rune key.
- `top_latin_ngram`: highest-count Latin phrase for that rune key.
- `source_file`: first source file contributing to the row.

## Cross-check status

Prototype tests cover:

- plain-row parsing
- rejection of `_end_`, quotes, apostrophes, and digit tokens
- strict versus normal dictionary filtering
- separate forward and reverse encoding
- WLI output being present and aligned to rune tokens
- empty output files when no rows survive filtering
