from types import SimpleNamespace

import pytest

from rdp import api
import rdp.solvers.seed_generation as seed_utils


@pytest.mark.parametrize(
    ("direction", "expected_token"),
    [
        (api.TextDirection.LEFT_TO_RIGHT, "ltr"),
        (api.TextDirection.RIGHT_TO_LEFT, "rtl"),
    ],
)
def test_unigram_seed_probe_converts_public_direction_at_lm_boundary(
    monkeypatch, direction, expected_token
):
    observed: list[str] = []

    class FakeLanguageModel:
        def __init__(self, **_kwargs):
            pass

        def score(self, plaintexts, _wli, *, direction, **_kwargs):
            observed.append(direction)
            return [SimpleNamespace(logprob_sum=0.0) for _ in plaintexts]

    monkeypatch.setattr(seed_utils, "LanguageModelPrime", FakeLanguageModel)

    probabilities = seed_utils._lm_unigram_probs(A=3, direction=direction)

    assert observed == [expected_token]
    assert probabilities == pytest.approx([1 / 3, 1 / 3, 1 / 3])
