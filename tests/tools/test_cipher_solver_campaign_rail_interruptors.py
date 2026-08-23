from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime import api
from tools.robustness import cipher_solver_campaign as campaign


pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize("trial_index", (6, 9, 12, 13))
def test_railfence_generation_uses_declared_search_range(trial_index: int) -> None:
    case = campaign.build_case("railfence_beam", trial_index)
    low = case.cipher_parameters["min_rails"]
    high = case.cipher_parameters["max_rails"]
    cipher = api.cipher_instance("railfence", min_rails=low, max_rails=high)

    recovered = cipher.decrypt(
        ciphertext=np.asarray(case.ciphertext, dtype=np.uint8),
        key=np.asarray(case.expected_key, dtype=np.uint8),
    )

    np.testing.assert_array_equal(recovered, case.reference)


def test_interruptor_campaign_uses_score_selected_beam_restarts() -> None:
    case = campaign.build_case("vigenere_interruptors_beam", 0)

    assert case.solver.name == "beam"
    assert case.solver.params["restarts"] == 3
