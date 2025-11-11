# `tutorials/v1/dev/Autokey.py`

> Purpose: explore a classical Autokey cipher variant using RDP's by‑name wrappers and RunAPI. This dev tutorial shows how to wire a key schedule into a map cipher and evaluate it with GA/SA baselines.

Audience: Hands‑on / Expert
Time: 8-12 minutes (CPU)
Outcome: Run an autokey demo and compare seeded vs unseeded search
Prereqs: Python 3.11+, repo installed (`pip install -e .[dev]`)

## What it does
- Builds a user map that uses previous plaintext symbols as part of the key stream.
- Encrypts a short English sample and attempts to recover using GA/SA.
- Logs telemetry under `output/tutorials/<run>/...` and prints a plaintext preview.

## Run command
```bash
python tutorials/v1/dev/Autokey.py --print-progress
```

## Expected output
- Deterministic progress lines and a final plaintext/key preview.
- `logs/app.jsonl` containing `telemetry.run` and `solver_progress` events.

## Related docs
- `docs/howto/add_cipher.md` - steps to promote a prototype into a reusable cipher.
- `docs/reference/api/maps_api.md` - UX helpers for user maps.

