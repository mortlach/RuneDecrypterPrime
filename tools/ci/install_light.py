from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_PY = REPO_ROOT / "install.py"


def _ensure_repo_root_importable() -> None:
    repo_root = str(REPO_ROOT)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _load_install_module():
    _ensure_repo_root_importable()
    spec = importlib.util.spec_from_file_location("rdp_install", INSTALL_PY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load installer: {INSTALL_PY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = _load_install_module()
    return module.run_install(
        asset_profile_name="ci_light",
        mode_label="CI light install",
    )


if __name__ == "__main__":
    raise SystemExit(main())
