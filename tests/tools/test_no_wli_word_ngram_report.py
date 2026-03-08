from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.scoring_experiment_config import (
    build_word_ngram_report_cfg,
)
from tools.benchmarks.periodic_sub_trans.no_wli import word_ngram_report as report_mod


pytestmark = pytest.mark.tier_a


def test_build_word_ngram_report_cfg_disabled_returns_none(tmp_path: Path) -> None:
    out = build_word_ngram_report_cfg(
        base_cfg={"objective": "avg.logp.win20"},
        direction="ltr",
        word_ngram_report_enabled=False,
        word_ngram_report_sqlite_path=tmp_path / "x.sqlite",
        word_ngram_report_alpha=0.4,
        word_ngram_report_miss_logp=-20.0,
        word_ngram_report_min_positions=12,
        word_ngram_report_prefix_total_thresholds=(1, 10, 100),
        resolve_repo_path_fn=lambda p: Path(p) if p is not None else None,
    )
    assert out is None


def test_build_word_ngram_report_cfg_enabled_sets_contract(tmp_path: Path) -> None:
    sqlite_fp = tmp_path / "word_ngrams.sqlite"
    sqlite_fp.write_text("", encoding="utf-8")
    out = build_word_ngram_report_cfg(
        base_cfg={"objective": "avg.logp.win20"},
        direction="ltr",
        word_ngram_report_enabled=True,
        word_ngram_report_sqlite_path=Path("tmp/word_ngrams.sqlite"),
        word_ngram_report_alpha=0.7,
        word_ngram_report_miss_logp=-15.0,
        word_ngram_report_min_positions=9,
        word_ngram_report_prefix_total_thresholds=(2, 20, 200),
        resolve_repo_path_fn=lambda _p: sqlite_fp,
    )
    assert out is not None
    assert bool(out.get("word_ngram_judge_enabled", False)) is True
    assert Path(str(out.get("word_ngram_judge_sqlite_path", ""))) == sqlite_fp
    assert float(out.get("word_ngram_judge_alpha", 0.0)) == pytest.approx(0.7)
    assert int(out.get("word_ngram_judge_min_positions", 0)) == 9
    assert tuple(out.get("word_ngram_judge_prefix_total_thresholds", ())) == (2, 20, 200)


def test_score_word_ngram_report_for_plaintext_uses_last_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def _fake_score_plaintexts_chunked(**kwargs):
        observed["require_batch"] = bool(kwargs.get("require_batch", False))
        observed["chunk_size"] = int(kwargs.get("chunk_size", -1))
        observed["n"] = len(list(kwargs.get("plaintexts", [])))
        return np.asarray([0.0], dtype=np.float32), {}

    class _FakeScorer:
        def last_stats(self):
            return {
                "word_ngram_judge_available": True,
                "word_ngram_judge_active": True,
                "word_ngram_judge_n_positions": 13,
                "word_ngram_judge_report_xent": 1.234,
                "word_ngram_judge_trust_score": 0.77,
                "word_ngram_judge_trust_tier": "medium",
            }

    monkeypatch.setattr(report_mod, "score_plaintexts_chunked", _fake_score_plaintexts_chunked)
    out = report_mod.score_word_ngram_report_for_plaintext(
        scorer_runtime=_FakeScorer(),
        plaintext_idx=[1, 2, 3, 4],
        wli=[],
        require_batch_scoring=True,
    )
    assert observed == {"require_batch": True, "chunk_size": 1, "n": 1}
    assert bool(out.get("word_ngram_judge_active", False)) is True
    assert int(out.get("word_ngram_judge_n_positions", 0)) == 13
    assert float(out.get("word_ngram_judge_report_xent", 0.0)) == pytest.approx(1.234)
    assert str(out.get("word_ngram_judge_trust_tier", "")) == "medium"
