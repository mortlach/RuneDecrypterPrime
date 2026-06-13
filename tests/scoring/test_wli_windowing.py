import numpy as np

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.scoring import rune_scorer


class _StubRt:
    def __init__(self, *_, **__):
        self.ecdf = object()


def test_wli_window_axis_order_is_L_by_2(monkeypatch):
    monkeypatch.setattr(rune_scorer, "LmPrimeRuntime", _StubRt)
    cfg = ScoringConfig(encoding_dir=Direction.LTR)
    c_cfg = CipherConfig(ciphertext=[], wli_data=[], key_length=None, encoding_dir=Direction.LTR)
    scorer = rune_scorer.RuneScorer(c_cfg, cfg)

    pt = np.arange(15, dtype=np.uint8)
    wli = np.stack(
        [np.arange(15, dtype=np.uint8), np.arange(1, 16, dtype=np.uint8)],
        axis=1,
    )

    pt_w_map, wli_w_map, _, nwin, _ = scorer._build_aligned_windows(
        pt, wli, n_set=[2], W=10, stride=1
    )

    assert nwin == 5
    w = wli_w_map[2]
    assert w.shape == (5, 11, 2)
    assert np.array_equal(w[0], wli[:11])
    assert np.array_equal(w[1], wli[1:12])
