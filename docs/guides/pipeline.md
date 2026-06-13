# Pipeline – Direction, Permutation, Device

Audience: Hands-on / Expert  
Time: 3–5 minutes  
Outcome: Know how to set text direction, permutations, and device hints when calling RunAPI.  
Prereqs: Completed one tutorial; skimmed `guides/architecture.md`.

---

## 1. Direction (`Direction.LTR` / `Direction.RTL`)
- Controls how ciphertext/plaintext is interpreted (left-to-right vs right-to-left rune order). Ciphers and scorers both honour this enum.
- Tutorials default to `Direction.LTR`. If you work with RTL alphabets or want to experiment with mirrored text, pass `encoding_dir=Direction.RTL`.
- RunAPI and the pipeline block capture direction so telemetry stays comparable. The API normalisers also accept friendly strings (`"ltr"`, `"rtl"`, `"fwd"`, `"rev"`).

---

## 2. Permutation (`initial_text_permutation_indices`)
- Optional list of integers (`len == ciphertext length`) that reorders the text **before** decrypt/scoring. Typical use-cases: reversing the text or applying a known columnar shuffle.
- Keep it deterministic: supply a true permutation (no duplicates, 0..L-1). The API will reject malformed lists.
- Telemetry pipeline block hashes the permutation so you can detect mismatched runs.

Example (reverse text before solving):
```python
from rune_decrypter_prime.api import run, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction

perm = list(reversed(range(200)))  # toy permutation
sol = run(
    text="ᛏᚻᛖᚱᛖ …",
    cipher=by_name.cipher("vigenere", key_len=6),
    key=KeySpec.repeat(len=6),
    solver=SolverSpec.ga(seed=1337, progress_pct=1),
    encoding_dir=Direction.LTR,
    initial_text_permutation_indices=perm,
    telemetry_on=True,
)
```

---

## 3. Device (`Device.CPU` / `Device.CUDA`)
- Drives backend selection for both cipher/scorer. CPU is the reference; CUDA (Torch) is available when PyTorch + GPU drivers are installed.
- Set via the `device` argument in RunAPI/SolverSpec or on the `CipherConfig`. The unified scorer records whatever backend was chosen.
- Even when you request CUDA, semantics stay the same: telemetry reports the backend so you can verify parity.

---

## 4. Recommended workflow
1. Keep direction and permutation explicit in tutorials/scripts so results are reproducible.
2. Stick with CPU while developing a new cipher/key model; switch to CUDA once you want speed. Always compare telemetry to ensure both runs match.
3. When debugging, inspect `telemetry.run.pipeline` in `output/<kind>/<run_id>/logs/app.jsonl` to confirm direction/permutation/device.

---

## Related docs/tests
- Docs: `guides/architecture.md`, `guides/telemetry.md`, `howto/deterministic_run.md`.
- Tests: `tests/pipeline/test_permutation_tracking.py`, `tests/telemetry/test_solver_pipeline_block.py`.
