# Runes And Text

Status: staged V1 draft

RDP works with a 29-rune alphabet.

Users often start with English-looking text, but the solver works on rune
indices. The conversion from English text to rune indices is important, and it
must be reported clearly.

## The Three Views

The same text can appear in three useful views:

| View | Meaning |
| --- | --- |
| English text | the input or display text a person reads |
| rune text | the visible runes |
| rune indices | the numeric symbols solvers and ciphers use |

Example shape:

```text
English text -> rune tokens -> rune indices
```

The solver usually works on the indices, not the English spelling.

## One Rune Can Mean Several Letters

In the RDP alphabet, one rune can represent one, two, or three Latin letters.

Examples of Latin rune tokens include:

```text
A
AE
TH
ING
EA
EO
OE
```

That means text rendering is not always a simple one-letter-at-a-time process.

## Canonical Normalisation

RDP uses canonical alphabet rules.

Some English spellings collapse to the same rune symbols. For example:

```text
K -> C
Q -> C
V -> U
Z -> S
```

So if a tutorial starts with:

```text
LOOKED
```

the recovered canonical Latin display may be:

```text
LOOCED
```

That is not a solver error. The original `K` spelling is not preserved by the
29-rune encoding.

## Encoding Direction

RDP uses an explicit text encoding direction:

```text
ltr
rtl
```

`ltr` means left-to-right tokenisation inside each word.

`rtl` means the word is handled in a right-to-left style before rune-token
boundaries are chosen, then represented back in normal display order.

This matters because multiletter rune tokens can cross different boundaries.

For example, under RTL encoding:

```text
READ
```

has rune-token display order:

```text
R AE D
```

If those tokens are naively joined left-to-right as Latin tokens, the display
looks like:

```text
RAED
```

That is wrong for a human plaintext display. The renderer must use the run's
`encoding_dir` to reconstruct the intended canonical Latin text:

```text
READ
```

## Why Reports Print encoding_dir

Every human-facing report that interprets plaintext shows:

```text
encoding_dir: rtl
```

or:

```text
encoding_dir: ltr
```

Without that field, a reader cannot tell how rune tokens were converted back
into Latin display text.

## Word-Location Information

RDP often carries WLI, short for word-location information.

WLI records where each rune token sits inside a word. It lets RDP render spaces
and apply word-aware scoring.

Direction-aware Latin display needs word boundaries. Without WLI, RDP can still
show rune indices or rune text, but it cannot always safely reconstruct the
intended English-like word spelling.

## What Solvers Compare

Tutorial match ratios usually compare rune indices, not raw English spelling.

That is why this can be true at the same time:

```text
match_ratio: 1.0
displayed plaintext: LOOCED
original teaching text: LOOKED
```

The rune-index recovery is exact. The spelling difference comes from canonical
alphabet normalisation.

## Practical Reading Rule

When checking tutorial output:

1. Look for `encoding_dir`.
2. Check the match ratio.
3. Remember that canonical spellings may differ from ordinary English spelling.
4. Treat missing direction as a report-quality problem.

For V1 pretty-print tutorials, the standard summary prints `encoding_dir`
before the plaintext block.
