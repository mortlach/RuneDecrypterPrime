from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import runner_defaults as defaults_mod


pytestmark = pytest.mark.tier_a


def test_apply_runner_defaults_enables_word_ngram_when_sqlite_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        defaults_mod,
        "_discover_word_ngram_sqlite_path",
        lambda: Path("output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/x.sqlite"),
    )
    state: dict[str, object] = {}
    defaults_mod.apply_runner_defaults(state=state)
    assert bool(state.get("WORD_NGRAM_REPORT_ENABLED", False)) is True
    assert Path(str(state.get("WORD_NGRAM_REPORT_SQLITE_PATH", ""))) == Path(
        "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/x.sqlite"
    )


def test_apply_runner_defaults_disables_word_ngram_when_sqlite_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(defaults_mod, "_discover_word_ngram_sqlite_path", lambda: None)
    state: dict[str, object] = {}
    defaults_mod.apply_runner_defaults(state=state)
    assert bool(state.get("WORD_NGRAM_REPORT_ENABLED", True)) is False
    assert state.get("WORD_NGRAM_REPORT_SQLITE_PATH") is None


def test_discover_word_ngram_sqlite_path_uses_repo_root_not_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_rel = Path(
        "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/"
        "run_x/word_ngrams_tokenized64_phase2_v1.sqlite"
    )
    asset_fp = tmp_path / asset_rel
    asset_fp.parent.mkdir(parents=True, exist_ok=True)
    asset_fp.write_text("", encoding="utf-8")

    other_cwd = tmp_path / "other_cwd"
    other_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(other_cwd)

    out = defaults_mod._discover_word_ngram_sqlite_path(repo_root=tmp_path)
    assert out == asset_rel
