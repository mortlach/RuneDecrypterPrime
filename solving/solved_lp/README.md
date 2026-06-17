# Solved LP workbook

This folder contains the human-facing solved Liber Primus workbook files. Each
file is meant to be opened and run directly.

```text
01_A_Warning.py
02_Welcome_Pilgrim.py
03_Some_Wisdom.py
04_Koan_A_Man.py
05_Loss_Of_Divinity.py
06_Koan_During_Lesson.py
07_Instruction.py
08_An_End.py
09_Parable.py
run_all.py
```

The files use LP source labels such as `welcome_pilgrim`, not raw page numbers.
Each file prints a final evidence block with:

```text
match_ratio: 1.000
status: solved
```

The simple pages replay their known recipe directly. `Welcome Pilgrim`,
`Koan During Lesson`, and `AN END` include pinned solve evidence for the
Vigenere/interrupter or sequence/interrupter cases so the workbook remains
readable and repeatable.

Page-name compatibility remains catalogue-owned. In particular, `p56`,
`56.jpg`, and `canon.56` resolve to `an_end`, which maps to main transcript
page 71; `p57`, `57.jpg`, and `canon.57` resolve to `parable`, which maps to
main transcript page 72.

To run one workbook file:

```text
python solving/solved_lp/02_Welcome_Pilgrim.py
```

To run the full workbook solve check:

```text
python solving/solved_lp/run_all.py
```
