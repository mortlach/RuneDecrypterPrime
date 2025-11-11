# Rune Decrypter Prime

Deterministic rune-cipher research lab for puzzle-solvers and advanced contributors. Tutorials, solvers, and telemetry tools are designed to be reproducible and auditable out of the box.

## Requirements
- CPython **3.11** (64-bit). Install from python.org. Earlier versions are not supported.
- Windows 10/11, macOS 13+, or a modern Linux distro.
- Optional: CUDA-capable GPU + PyTorch if you want to run the Torch scorer.
- Git, C/C++ build chain (only required when rebuilding the optional fast LM extension).

## Installation

```
# 1. clone
git clone https://github.com/your-org/RuneDecrypterPrime.git
cd RuneDecrypterPrime

# 2. create + activate a virtual environment
python -m venv .venv
# Windows
.\\.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

# 3. install the package (dev extras include pytest/ruff etc.)
pip install -U pip
pip install -e .[dev]
```

> **Skipping Torch?** Set `set RDP_TORCH=0` (Windows) or `export RDP_TORCH=0` (macOS/Linux) **before** installing to skip the heavy torch wheel on CPU-only machines.

## Optional: build the fast LM extension
The NumPy scorer streams ~1.2 GB of language-model tables. On Windows the prebuilt `_fastlm.cp311-win_amd64.pyd` ships in the repo; on Linux/macOS you must build it once:

```
# from repo root with the venv activated
python src/rune_decrypter_prime/scoring/language_model/setup_fastlm.py
```

The script produces `_fastlm.<platform>.so/.pyd` next to `fastlm.cpp`. Re-run it whenever you switch Python versions.

## Quick Start (5 minutes)
1. Activate your virtualenv.
2. Run the lightweight intro tutorial:
   ```
   python tutorials/v1/Start_Here.py
   ```
   You should see two runs:
   ```
   [Wrapper Beam] score=0.69
     Plaintext: ᛏᚻᛖᚱᛖ ᚹᚪᛋ ᚪ ᛏᚪᛒᛚᛖ ᛋᛖᛏ …
     Key: [3, 1, 4, 1]

   [General Map Beam] score=0.03
     Plaintext: …
     Key: [13, 0, 24, 28]
   ```
3. Inspect the run logs under `output/tutorials/<timestamp>__tutorials__start_here__nogit/`.

Need a meatier example? Run `python tutorials/v1/Tutorial_Vigenere_GeneralMap.py --print-progress` to watch beam search converge.

## Running tests
- Tier-A smoke (sub-5 s CPU): `pytest -m tier_a`
- Full suite: `pytest`
- Single tutorial regression: `pytest tests/tutorials/test_pct_win10_stats_and_telemetry.py::test_pct_win10_wli_numpy_vs_list_equivalence`

All test artifacts land under `output/tests/<timestamp>__tests__pytest__<git>/`.

## Output & Telemetry
Every run initialises a logging root via `LoggingConfig`:
```
output/
  tests/<ts>__tests__pytest__abcd123/
    META.json         # repo-relative paths, CPU info, seeds
    logs/app.jsonl    # telemetry events
    trace/            # optional cProfile dumps
    artifacts/tests/<nodeid>/  # per-test scratch space
  tutorials/<ts>__tutorials__/.../
  share/<ts>__share__/.../
```
Nothing writes outside `output/`. If you need to share results, copy the entire run directory.

## Documentation map
- `docs/INDEX.md` – table of contents.
- `docs/setup/installation.md` – step-by-step install (desktop + CI).
- `docs/guides/quickstart.md` – language-model overview, solver tips.
- `docs/guides/architecture.md` – pipeline diagram from API → solver.
- `docs/appendices/high_school_troubleshooting.md` – “it broke, now what?” playbook.

## Tips for contributors
- Keep seeds explicit (`SolverSpec.*(seed=1234)`) so runs are reproducible.
- Leave `progress_pct=1` and `print_progress=False` in CI; enable printing only for demos/tutorials.
- Run Tier-A + relevant tutorials before submitting PRs.
- Ensure `_fastlm` is rebuilt after upgrading Python.
- Only add writable directories under `output/`.

Happy decrypting!
