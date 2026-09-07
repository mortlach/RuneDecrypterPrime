# Solved LP workbook

The workbook contains nine solved Liber Primus examples plus `run_all.py`.

Run one file directly:

```text
python solving/solved_lp/02_Welcome_Pilgrim.py
```

Run the workbook check with:

```text
python solving/solved_lp/run_all.py
```

## Evidence classes

| File | Method | Evidence class | Truth use |
| --- | --- | --- | --- |
| `01_A_Warning.py` | reverse-gematria recipe | deterministic replay | known recipe defines the transform |
| `02_Welcome_Pilgrim.py` | period-8 Vigenere + interruptor search | independent recovery checked afterwards | known period, interruptor count and zero-position pool supplied. Key values and exact positions searched. Canonical plaintext used after the run |
| `03_Some_Wisdom.py` | shift-0 recipe | deterministic replay | known recipe defines the transform |
| `04_Koan_A_Man.py` | rotated reverse-gematria recipe | deterministic replay | known shift/recipe defines the transform |
| `05_Loss_Of_Divinity.py` | shift-0 recipe | deterministic replay | known recipe defines the transform |
| `06_Koan_During_Lesson.py` | pinned period-13 Vigenere/interruptor result | deterministic replay | known recovered key and interruptor positions are supplied directly |
| `07_Instruction.py` | shift-0 recipe | deterministic replay | known recipe defines the transform |
| `08_An_End.py` | sequence-shape reconstruction | reference-guided diagnostic | canonical plaintext can participate in attempt ranking and selection |
| `09_Parable.py` | shift-0 recipe | deterministic replay | known recipe defines the transform |

The label `solved_lp` means the source is solved and the workbook records work
around that solution. It does not mean every file independently recovers
its solution.

## Welcome Pilgrim

`02_Welcome_Pilgrim.py` is the main solver-recovery example in this workbook.

The run is given:

```text
cipher family: Vigenere
key length: 8
interruptor count: 11
candidate interruptor pool: ciphertext-zero positions
```

It is not given the key values or the exact interruptor positions.

The canonical plaintext is used after the run to calculate the match ratio and
acceptance result.

It is a recovery from stated prior information, not a blind solve.

## Koan During Lesson

`06_Koan_During_Lesson.py` replays a pinned key and pinned interruptor positions
through the runtime cipher.

It checks the solved transformation and source alignment.

It is not a solver search.

## AN END

`08_An_End.py` is a structured reconstruction/diagnostic.

It explores sequence families, offsets, phrase starts and interruptor semantics.
When the canonical plaintext reference is present, the attempt sort uses the
reference match ratio.

The known answer is therefore part of candidate ranking.

Keep the example under `solved_lp` because it is work on a solved source, but
describe it as reference-guided rather than independent recovery.

## Source labels

The workbook loads LP sources through registered labels rather than copied
ciphertext.

Page aliases remain catalogue-owned. For example, the `an_end` and `parable`
aliases resolve through the current LP source registry.

For the public LP data interface, see
[Liber Primus data](../../docs/reference/liber_primus.md).
