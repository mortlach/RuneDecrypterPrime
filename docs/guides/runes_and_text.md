# Runes and text

RDP works with a 29-rune alphabet. A person may begin with Latin text or visible
runes; ciphers and solvers ultimately operate on rune indices.

## Three related views

| View | What it records |
| --- | --- |
| Latin text | A readable source or display form. |
| Rune text | The visible rune sequence, including word boundaries. |
| Rune indices | Numeric symbols from 0 to 28 used at cipher boundaries. |

The first getting-started file keeps all three reviewed forms together. The
public known-key operations accept indices; RDP does not smuggle an internal
Latin encoder into that example for convenience.

## Multi-letter tokens and normalisation

One rune may represent more than one Latin letter. Tokens include `TH`, `ING`,
`AE`, `EA`, `EO` and `OE`. Canonical alphabet rules also collapse some ordinary
spellings:

```text
K -> C
Q -> C
V -> U
Z -> S
```

Exact rune recovery can therefore coexist with a canonical Latin rendering
that differs from the original spelling. Compare indices when the scientific
claim is exact rune recovery.

## Direction is data

RDP records text direction explicitly:

- `TextDirection.LEFT_TO_RIGHT` (`left_to_right`)
- `TextDirection.RIGHT_TO_LEFT` (`right_to_left`)

Direction affects tokenisation within words, especially around multi-letter
runes. It is not a cosmetic display toggle. A report that interprets plaintext
without its direction is missing relevant evidence.

## Word-location information

Word-location information (WLI) records each rune’s offset and word length. It
allows word-aware scoring, preserves spaces, and gives a direction-aware
renderer enough structure to rebuild readable text.

`api.RawTextInput` derives indices and WLI from rune text. `api.RuneIndexInput`
accepts reviewed indices and optional WLI directly. Use the form that reflects
the evidence actually available; do not invent word boundaries merely to make
a score look better.

## A practical reading rule

When reviewing a run:

1. confirm the text direction;
2. distinguish displayed text from the rune-index sequence;
3. check whether WLI was supplied or inferred;
4. compare the result using the same representation as the stated claim.

The next useful document is the complete
[`example catalogue`](../../tutorials/v1/README.md).
