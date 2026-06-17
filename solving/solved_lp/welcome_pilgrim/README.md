# welcome_pilgrim

Run:

```text
python solving/solved_lp/welcome_pilgrim/solve.py
```

Source label:

```text
welcome_pilgrim
```

Recipe:

```text
recipe.welcome_pilgrim.vigenere_interruptors
```

Current confirmed model:

```text
cipher: Vigenere with interrupters
key_text_hint: DIVINITY
key_length: 8
interrupter_count: 11
interrupter_pool: all ciphertext-zero positions
```

The script searches using the zero-position pool, prints the found key,
interrupters, score, stop reason, telemetry timing, plaintext, and exact match
ratio. It reports `status: solved` only when the recovered plaintext matches
the canonical reference exactly.

The tutorial wrapper at `tutorials/v1/Tutorial_LP_Welcome_Pilgrim_Solve.py`
delegates here and should stay thin.

The readable workbook copy is:

```text
python solving/solved_lp/workbook/02_Welcome_Pilgrim.py
```
