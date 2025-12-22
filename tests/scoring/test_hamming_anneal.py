from __future__ import annotations

import pytest

from rune_decrypter_prime.scoring.hamming.anneal import compute_hamming_weight


@pytest.mark.parametrize(
    "progress,expected",
    [
        (0.0, 0.0),
        (0.1, 0.0),          # before ramp_start
        (0.2, 0.0),          # at ramp_start
        (0.45, 0.05),        # halfway ramp for w_max=0.1 between 0.2 and 0.7
        (0.7, 0.1),          # at ramp_end
        (0.9, 0.1),          # after ramp_end
    ],
)
def test_compute_hamming_weight_linear(progress, expected):
    w = compute_hamming_weight(progress, w_max=0.1, ramp_start=0.2, ramp_end=0.7)
    assert w == pytest.approx(expected, rel=1e-6, abs=1e-6)


def test_compute_hamming_weight_handles_inverted_ramp():
    # If ramp_end < ramp_start, function should swap them and still work.
    w = compute_hamming_weight(0.5, w_max=0.2, ramp_start=0.8, ramp_end=0.3)
    # ramp interpreted as 0.3 -> 0.8, so 0.5 is 40% through the ramp: 0.2 * 0.4 = 0.08
    assert w == pytest.approx(0.08, rel=1e-6, abs=1e-6)
