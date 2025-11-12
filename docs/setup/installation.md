# Installation

Everyone follows the same deterministic workflow: install Python 3.11, create a
virtual environment, install the package in editable mode, and keep all outputs
under `output/`. The steps below work for both GUI-first and CLI-only setups.

## 1. Install prerequisites
1. **Python 3.11 (64-bit).** Download from [python.org](https://www.python.org/downloads/)
   or use your OS package manager. Verify with:
   ```
   python --version
   # -> Python 3.11.x
   ```
2. **Git** (optional but recommended) so you can pull updates and track changes.
3. **C/C++ build tools** (only needed if you plan to rebuild the optional
   `_fastlm` extension on Linux/macOS).

## 2. Clone the repo
```bash
git clone https://github.com/your-org/RuneDecrypterPrime.git
cd RuneDecrypterPrime
```

## 3. Create & activate a virtual environment
### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Use `deactivate` to exit the environment when you are done.

## 4. Install dependencies
Inside the activated venv:
```bash
pip install -U pip
pip install -e .[dev]
```

- This installs NumPy, pytest, ruff, and Torch CPU by default.
- **Skipping Torch?** Set the env var *before* the install command:
  - Windows PowerShell: `set RDP_TORCH=0`
  - macOS/Linux: `export RDP_TORCH=0`

## 5. (Optional) Build the fast LM extension
Windows ships with `_fastlm.cp311-win_amd64.pyd`. On macOS/Linux run:
```bash
python src/rune_decrypter_prime/scoring/language_model/setup_fastlm.py
```
This builds `_fastlm.<platform>.so` next to `fastlm.cpp`. Re-run it whenever you
change Python versions.

## 6. Verify the install
1. **Run the quick tutorial:**
   ```bash
   python tutorials/v1/Start_Here.py
   ```
   Expect two runs (Wrapper Beam / General Map GA). Logs land under
   `output/tutorials/<timestamp>__tutorials__start_here__nogit/`.
2. **Run Tier-A tests (fast smoke):**
   ```bash
   pytest -m tier_a
   ```

If both commands succeed, you’re ready to build your own ciphers/solvers.

## 7. Optional tooling extras (contributors)
```bash
pip install -e .[dev,docs]
pre-commit install
```
This installs doc build deps and hooks. Use the CLI for automation; IDEs are
optional as long as they respect the same virtualenv.

## Shared tips
- Always activate the venv in new shells before running tutorials/tests.
- Keep `progress_pct=1`, set `print_progress=True` only when teaching; leave it
  `False` in CI.
- Every script writes under `output/<kind>/<run_id>/...`. If you add new tools,
  send their artefacts there too.
- On Windows, `set PYTHONUTF8=1` avoids encoding issues in telemetry JSONL.

