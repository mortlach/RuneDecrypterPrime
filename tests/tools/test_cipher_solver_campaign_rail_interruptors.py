from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from tools.robustness import cipher_solver_campaign as campaign

pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize("trial_index", (6, 9, 12, 13))
def test_railfence_generation_uses_declared_search_range(trial_index: int) -> None:
    case = campaign.build_case("railfence_beam", trial_index)
    low = case.cipher_parameters["min_rails"]
    high = case.cipher_parameters["max_rails"]
    recovered = api.decrypt(
        tuple((int(value) for value in case.ciphertext)),
        cipher=api.CipherSpec.rail_fence(minimum_rails=low, maximum_rails=high),
        key=tuple((int(value) for value in case.expected_key)),
    )
    np.testing.assert_array_equal(recovered, case.reference)


def test_interruptor_campaign_uses_score_selected_beam_restarts() -> None:
    case = campaign.build_case("vigenere_interruptors_beam", 0)
    assert case.solver.kind is api.advanced.SolverKind.BEAM_SEARCH
    assert case.solver.parameters["restarts"] == 3
