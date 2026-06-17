# Solved LP workspace

This folder is the local workspace for solved Liber Primus sections.

Rules:

- one solved source label per folder;
- one obvious runnable file per section: `solving/solved_lp/<section_label>/solve.py`;
- one human-facing workbook folder: `solving/solved_lp/workbook/`;
- normal workflows use LP source labels, not raw page numbers;
- each worked example shows its own loading/reporting steps directly;
- diagnostic scripts must print `status: diagnostic_not_yet_solved` and must not fake a solved pass.

Known solved source labels:

```text
warning
welcome_pilgrim
some_wisdom
koan_a_man
loss_of_divinity
koan_during_lesson
instruction
an_end
parable
```

Each `solve.py` loads its payload through:

```python
from rune_decrypter_prime.data import liber_primus as lp

payload = lp.payload_from_label(SOURCE_LABEL)
```

Page-name compatibility remains catalogue-owned. In particular, `p56`,
`56.jpg`, and `canon.56` resolve to `an_end`, which maps to main transcript
page 71; `p57`, `57.jpg`, and `canon.57` resolve to `parable`, which maps to
main transcript page 72.

`welcome_pilgrim/solve.py` is the only current runnable solver attempt. Its
current bounded Vigenere/interrupter settings are diagnostic because the known
match is poor. Keep it honest until the settings are improved.

For browsing, use the readable files in `workbook/`, for example:

```text
python solving/solved_lp/workbook/02_Welcome_Pilgrim.py
```
