from __future__ import annotations

import importlib
from pathlib import Path


def test_rune_scorer_does_not_require_experimental_word_ngram_module_at_import_time() -> None:
    module = importlib.import_module("rune_decrypter_prime.scoring.rune_scorer")
    assert hasattr(module, "RuneScorer")


def test_experimental_word_ngram_import_is_lazy_and_explicit() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / "src" / "rune_decrypter_prime" / "scoring" / "rune_scorer.py"
    text = source.read_text(encoding="utf-8")

    forbidden = "from rune_decrypter_prime.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime"
    first_lines = "\n".join(text.splitlines()[:80])

    assert forbidden not in first_lines
    assert "word_ngram_judge_enabled=True, but the experimental word-ngram" in text
    assert "install the experimental" in text
