# Installation

Two parallel tracks keep the repo approachable for high school Hands-ons and expert contributors. Both tracks share the **same deterministic seeds** and **output/** folder.

## Track 1 - Hands-on (GUI friendly)
1. **Install Python 3.11.** Download it from python.org (or your platform package manager) and make sure python --version reports 3.11.x.
2. **Clone or unzip the repo** into a writable folder with an output/ subdirectory (create it once if missing).
3. **Create a virtual environment** from your IDE or from PowerShell:
   `powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   `
4. **Install dependencies** with pip (inside the venv):
   `powershell
   pip install -e .[dev]
   `
   This installs NumPy, tqdm, pytest, and Torch CPU. Set RDP_TORCH=0 before the pip command if the machines should skip Torch.
5. **Mark sources (IDE only).** In PyCharm/VS Code mark src/ as the source root so imports resolve without editing PYTHONPATH.
6. **Run a tutorial** (either from the IDE Run button or from the terminal):
   `powershell
   python tutorials/v1/Tutorial_MonoSubstitution_GA.py --print-progress
   `
   Every run writes into output/tutorials/<timestamp>__tutorials__v1__<git>/.

## Tier 2 - Expert / CLI
1. **Clone** the repo and keep .git intact: git clone https://github.com/your-org/RuneDecrypterPrime.git.
2. **Bootstrap tools env**:
   `powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -e .[dev,docs]
   pre-commit install
   `
3. **Run the Tier-A tests** before editing:
   `powershell
   pytest -m tier_a
   `
4. **Regenerate docs/tools outputs** (all land in output/):
   - python tools/repo_utils/index_project_symbols.py
   - python tools/repo_utils/share_package.py
   - python tools/repo_utils/make_release_src.py
5. **Prefer CLI for automation.** IDEs remain optional; everything (tests, tutorials, telemetry dumps) is runnable via python ... or pytest ....

## Shared Tips
- Activate the virtual environment in every shell before running tutorials/tests.
- Keep progress_pct=1 and flip print_progress=True only when teaching; leave it False in CI shells.
- If a command needs to write files, point it at output/<kind>/... (the helper scripts already do this).
- When working on Windows, set PYTHONUTF8=1 to avoid encoding surprises in telemetry JSON.


