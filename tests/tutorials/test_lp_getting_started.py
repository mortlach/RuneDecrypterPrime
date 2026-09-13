import pytest

from rdp import api

from solving.getting_started.prepare_search import (
    INTERRUPTOR_COUNT,
    KEY_LENGTH,
    build_request,
)

pytestmark = pytest.mark.tier_a


def test_lp_getting_started_builds_reviewed_request() -> None:
    request = build_request()

    assert request.problem_input.ref["label"] == "red_rune.welcome_pilgrim"
    assert request.cipher.kind.value == "vigenere"
    assert request.key_space.parameters["length"] == KEY_LENGTH
    assert request.text_direction is api.TextDirection.LTR
    assert request.interruptors.parameters["minimum_count"] == INTERRUPTOR_COUNT
    assert request.interruptors.parameters["maximum_count"] == INTERRUPTOR_COUNT
    assert len(request.interruptors.parameters["candidate_positions"]) == 25
