# Tutorial - Vigenere with Interruptors (Exact Positions)

Audience: Hands-on  
Time: 3-5 minutes  
Outcome: Encrypt/decrypt while preserving fixed interruptor positions  
Prereqs: Python 3.11+, quickstart complete

Goal
- Show that interruptor symbols are removed before encryption and reinserted unchanged.

Steps
1. Open `tutorials/v1/Tutorial_Vigenere_Interruptors.py`.
2. Adjust `KEY` and `INTERRUPTORS` (zero-based absolute positions).
3. Run the script and confirm the printed interruptor symbols match between plaintext and ciphertext.
4. Confirm the recovered plaintext matches the original (see the report output).

Shape of the code
```python
cipher = cipher_instance("vigenere", key_length=len(KEY), text_transposition=direction.value)
ct_idx = cipher.encrypt_single(
    plaintext=pt_idx,
    key=np.asarray(KEY, dtype=np.uint8),
    interrupt_idx=INTERRUPTORS,
)

solution = run(
    text=ct_idx,
    cipher=by_name.cipher("vigenere"),
    key=KeySpec.repeat(len=len(KEY)),
    solver=SolverSpec.beam(beam_width=1, test_key=KEY),
    interruptors_exact=INTERRUPTORS,
)
```

Notes
- `interruptors_exact` uses absolute positions in the full text, zero-based.
- Interruptor values are preserved; the pipeline strips them before encryption and reinserts them after.
- If both are provided, `interruptors_exact` overrides any `interruptors_pool` settings.

Related tests
- `tests/ciphers/test_interruptors_exact.py`

