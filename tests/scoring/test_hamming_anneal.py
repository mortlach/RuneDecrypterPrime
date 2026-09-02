from __future__ import annotations
import pytest
from rdp.scoring.hamming.anneal import compute_hamming_weight

@pytest.mark.parametrize('progress,expected', [(0.0, 0.0), (0.1, 0.0), (0.2, 0.0), (0.45, 0.05), (0.7, 0.1), (0.9, 0.1)])
def test_compute_hamming_weight_linear(progress, expected):
    w = compute_hamming_weight(progress, w_max=0.1, ramp_start=0.2, ramp_end=0.7)
    assert w == pytest.approx(expected, rel=1e-06, abs=1e-06)

def test_compute_hamming_weight_handles_inverted_ramp():
    w = compute_hamming_weight(0.5, w_max=0.2, ramp_start=0.8, ramp_end=0.3)
    assert w == pytest.approx(0.08, rel=1e-06, abs=1e-06)
