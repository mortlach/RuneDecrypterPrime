from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "get_src_zip" / "zip_src_nobloat.py"


def _load():
    spec = importlib.util.spec_from_file_location("rdp_a5_zip_src", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_archive_bytes_ignore_source_mtime_and_host_metadata(tmp_path):
    mod = _load()
    repo = tmp_path / "repo"; src = repo / "src" / "pkg"; src.mkdir(parents=True)
    a = src / "a.py"; b = src / "b.py"
    a.write_bytes(b"print('a')\n"); b.write_bytes(b"print('b')\n")
    z1 = tmp_path / "one.zip"; z2 = tmp_path / "two.zip"
    mod.make_zip_src_nobloat(repo_root=repo, src_root=repo / "src", output_root=tmp_path, zip_path_override=z1)
    os.utime(a, (2_000_000_000, 2_000_000_000)); os.utime(b, (1_000_000_000, 1_000_000_000))
    mod.make_zip_src_nobloat(repo_root=repo, src_root=repo / "src", output_root=tmp_path, zip_path_override=z2)
    assert z1.read_bytes() == z2.read_bytes()
    with ZipFile(z1) as zf:
        assert zf.namelist() == ["src/pkg/a.py", "src/pkg/b.py"]
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in zf.infolist())
        assert zf.read("src/pkg/a.py") == b"print('a')\n"
