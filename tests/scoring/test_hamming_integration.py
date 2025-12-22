from __future__ import annotations

import csv
import numpy as np
import pytest
from pathlib import Path

from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.scoring import rune_scorer
from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists, _PACKAGE_DEFAULT_DIR
from rune_decrypter_prime.scoring.hamming.backend import HammingBackend
from rune_decrypter_prime.utils.runeglish import Runeglish

try:
    import rune_decrypter_prime.scoring.hamming._hamming as _h  # noqa: F401
    _EXT_AVAILABLE = True
except Exception:  # pragma: no cover
    _EXT_AVAILABLE = False


requires_ext = pytest.mark.skipif(not _EXT_AVAILABLE, reason="Hamming extension not built")


class _StubRt:
    """Minimal LM runtime stub that returns zero pct scores."""

    def __init__(self, *_, **__):
        self.ecdf = None

    def _bucket(self, *args, **kwargs):
        pt_w = args[-1] if args else kwargs.get("pt_w")
        nwin = pt_w.shape[0] if hasattr(pt_w, "shape") else len(pt_w or [])
        return {"pct": {"logp": np.zeros((nwin,), dtype=np.float32)}}

    score_char_nose = score_char_wise = score_wli_nose = score_wli_wise = _bucket


@requires_ext
def test_hamming_affects_rune_scorer(monkeypatch):
    # Use packaged wordlists; take a length-1 word so HD math is deterministic.
    wl_ltr, _ = load_raw1grams_wordlists()
    assert wl_ltr and 1 in wl_ltr, "Packaged hamming wordlists should include length-1 entries"
    word = wl_ltr[1][0]
    wli = [[0, 1]]

    # Ensure small window to avoid early return; stub LM runtime.
    monkeypatch.setattr(rune_scorer, "WIN_FIXED", 1)
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)

    cfg = ScoringConfig(
        hamming_enabled=True,
        hamming_weight=1.0,
        hamming_wordlist_dir=None,  # packaged default
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    assert scorer._hamming_backend is not None, "Hamming backend should be initialised"

    # Exact match -> hamming_total=0, score is the LM floor (1e-6).
    s_match = scorer.score(word, wli)
    assert s_match == pytest.approx(1e-6, rel=0, abs=1e-8)

    # Single-symbol word: changing rune by +1 ensures HD=1.
    backend = scorer._hamming_backend
    mutated = [(word[0] + 1) % 29]
    hd_mut = backend.total_min_hd(mutated, wli, direction=Direction.LTR)
    assert hd_mut == 1

    s_miss = scorer.score(mutated, wli)
    assert s_miss == pytest.approx(s_match - hd_mut, rel=1e-6, abs=1e-6)


@requires_ext
def test_selected_vs_unselected_words_have_correct_hd(monkeypatch):
    base: Path = _PACKAGE_DEFAULT_DIR
    assert base.exists(), "Packaged hamming_raw_1g data must exist"

    wl_ltr, _ = load_raw1grams_wordlists()
    backend = HammingBackend(wl_ltr, None, max_hd=10)

    samples: list[tuple[int, list[str], list[str]]] = []
    for length in range(1, 6):
        fname = base / f"raw1grams_{length:02d}.csv"
        if not fname.exists():
            continue
        selected: list[str] = []
        unselected: list[str] = []
        with fname.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 4:
                    continue
                rune_str = row[3]
                flag = row[2].strip()
                if flag == "1" and len(selected) < 5:
                    selected.append(rune_str)
                if flag != "1" and len(unselected) < 5:
                    unselected.append(rune_str)
                if len(selected) >= 5 and len(unselected) >= 5:
                    break
        samples.append((length, selected, unselected))

    # Selected entries must match exactly; unselected must incur distance.
    for length, selected, unselected in samples:
        for rune_str in selected:
            idx = Runeglish.rune_to_pos(rune_str)
            wli = [[i, length] for i in range(length)]
            hd = backend.total_min_hd(idx, wli, direction=Direction.LTR)
            assert hd == 0, f"Selected word {rune_str} (len {length}) should match exactly"
        hd_positive = 0
        for rune_str in unselected:
            idx = Runeglish.rune_to_pos(rune_str)
            wli = [[i, length] for i in range(length)]
            # Some unselected entries may duplicate selected runes; only check those absent from the dictionary.
            if idx in wl_ltr.get(length, []):
                continue
            hd = backend.total_min_hd(idx, wli, direction=Direction.LTR)
            assert hd > 0, f"Unselected word {rune_str} (len {length}) should incur HD > 0"
            hd_positive += 1
        if unselected:
            assert hd_positive >= 1, f"Expected at least one unique unselected word with HD>0 for len {length}"

    # Integration: scorer should penalise an unselected word compared to a selected one.
    pair = next(((l, s[0], u[0]) for l, s, u in samples if s and u), None)
    if pair is None:
        pytest.skip("No length found with both selected and unselected samples")
    length, sel_rune, unsel_rune = pair
    sel_idx = Runeglish.rune_to_pos(sel_rune)
    unsel_idx = Runeglish.rune_to_pos(unsel_rune)
    wli = [[i, length] for i in range(length)]

    monkeypatch.setattr(rune_scorer, "WIN_FIXED", 1)
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    cfg = ScoringConfig(
        hamming_enabled=True,
        hamming_weight=1.0,
        encoding_dir=Direction.LTR,
    )
    fake_cipher = type("C", (), {"device": "cpu"})
    scorer = rune_scorer.RuneScorer(fake_cipher, cfg)
    assert scorer._hamming_backend is not None

    score_sel = scorer.score(sel_idx, wli)
    score_unsel = scorer.score(unsel_idx, wli)
    assert score_unsel < score_sel, "Unselected word should score worse due to HD penalty"
