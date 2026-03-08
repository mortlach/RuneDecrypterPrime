from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.common import paths


pytestmark = pytest.mark.tier_a


def test_make_flavor_run_dir_is_unique_on_quick_repeats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "output_root", lambda: tmp_path)
    d1 = paths.make_flavor_run_dir(flavor="x", run_prefix="bench")
    d2 = paths.make_flavor_run_dir(flavor="x", run_prefix="bench")
    assert d1 != d2
    assert d1.exists()
    assert d2.exists()


def test_make_flavor_run_dir_collision_fallback_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "output_root", lambda: tmp_path)
    monkeypatch.setattr(paths, "run_tag", lambda default="nogit": "tag123")

    fixed_stamp = "20260308T010203123456Z"

    class _FixedNow:
        @staticmethod
        def now(_tz):
            from datetime import datetime, timezone

            return datetime(2026, 3, 8, 1, 2, 3, 123456, tzinfo=timezone.utc)

    monkeypatch.setattr(paths, "datetime", _FixedNow)

    out = tmp_path / "periodic_sub_trans" / "x"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{fixed_stamp}__bench__tag123").mkdir(parents=True, exist_ok=True)

    d = paths.make_flavor_run_dir(flavor="x", run_prefix="bench")
    assert d.name.endswith("__r1")
    assert d.exists()

