from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Local full-assets proof: set this single constant to the verified external V1
# assets root. Do not add an environment-variable or CWD fallback.
EXTERNAL_ASSETS_ROOT: Path | None = None
TUTORIAL_REL = Path("tutorials/v1/Tutorial_Autokey.py")
PROJECT_ROOT = Path(__file__).resolve().parents[2]

_PATH_INJECTION = '''_ROOT = Path(__file__).resolve().parents[2]\n_SRC = _ROOT / "src"\nif str(_SRC) not in sys.path:\n    sys.path.insert(0, str(_SRC))\n'''


def main() -> int:
    if EXTERNAL_ASSETS_ROOT is None:
        raise SystemExit("Set EXTERNAL_ASSETS_ROOT at the top of this file to the verified full_v1 assets root.")
    lm_root = (Path(EXTERNAL_ASSETS_ROOT).resolve() / "language_model" / "lmp")
    if not (lm_root / "index.json").is_file():
        raise FileNotFoundError(f"verified LM root missing index.json: {lm_root}")
    source = PROJECT_ROOT / TUTORIAL_REL
    text = source.read_text(encoding="utf-8")
    if _PATH_INJECTION not in text:
        raise RuntimeError("tutorial source-path injection stanza changed; review before updating proof")
    text = text.replace(_PATH_INJECTION, "", 1)
    marker = "    scorer_params = dict(\n"
    if marker not in text:
        raise RuntimeError("tutorial scorer_params anchor changed; review before updating proof")
    text = text.replace(marker, marker + f"        model_root=Path({str(lm_root)!r}),\n", 1)
    with tempfile.TemporaryDirectory(prefix="rdp_a5_installed_tutorial_") as td:
        copied = Path(td) / source.name
        copied.write_text(text, encoding="utf-8", newline="\n")
        proc = subprocess.run([sys.executable, str(copied)], cwd=td, text=True, encoding="utf-8", errors="replace",
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(proc.stdout, end="")
        if proc.returncode:
            raise SystemExit(proc.returncode)
        print("[a5-installed-tutorial] PASS: copied tutorial ran without repository src injection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
