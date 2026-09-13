"""Output location policy; safe to load before installing RDP dependencies."""
from __future__ import annotations
import os
import tempfile
import tomllib
from pathlib import Path


def source_root(start: Path | None = None) -> Path | None:
    anchor = (start or Path(__file__)).resolve()
    for candidate in (anchor, *anchor.parents):
        manifest = candidate / "pyproject.toml"
        if manifest.is_file() and (candidate / "src/rdp/core/config/output_paths.py").is_file():
            with manifest.open("rb") as stream:
                if tomllib.load(stream).get("project", {}).get("name") == "rune-decrypter-prime":
                    return candidate
    return None


def resolve_output_root(explicit: Path | None = None) -> Path:
    """Explicit path > absolute inherited root > source output > OS user data."""
    if explicit is not None:
        root = explicit.resolve()
    elif "RDP_OUTPUT_ROOT" in os.environ:
        value = os.environ["RDP_OUTPUT_ROOT"]
        if not value.strip() or not Path(value).is_absolute():
            raise ValueError("RDP_OUTPUT_ROOT must be a nonempty absolute path")
        root = Path(value).resolve()
    else:
        checkout = source_root()
        if checkout is not None:
            root = checkout / "output"
        else:
            from platformdirs import user_data_path
            root = user_data_path("RuneDecrypterPrime", appauthor=False, roaming=False) / "output"
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=root):
        pass  # Fail here when the chosen destination is not writable.
    return root


def path_from(path: Path, base: Path) -> str:
    """A usable path from base, including Windows destinations on another drive."""
    try:
        return os.path.relpath(path, base)
    except ValueError:
        return str(path)
