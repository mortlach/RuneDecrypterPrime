from __future__ import annotations
import rdp.api.data_helpers
from dataclasses import dataclass
import pytest

pytestmark = pytest.mark.tier_a


@dataclass(frozen=True)
class _Payload:
    ct_idx: list[int]
    wli: list[list[int]]
    metadata: dict[str, object]


def test_load_lp_payload_from_label_delegates_to_catalogue(monkeypatch) -> None:
    from rune_decrypter_prime.data.liber_primus import lp_source_catalogue

    def fake_payload_from_label(label: str):
        assert label == "red_rune.welcome_pilgrim"
        return _Payload(
            ct_idx=[1, 2, 3],
            wli=[[0, 3], [1, 3], [2, 3]],
            metadata={"source_label": label},
        )

    monkeypatch.setattr(
        lp_source_catalogue, "payload_from_label", fake_payload_from_label
    )
    payload = rdp.api.data_helpers.load_lp_payload_from_label(
        "red_rune.welcome_pilgrim"
    )
    assert payload.ct_idx == [1, 2, 3]
    assert payload.metadata["source_label"] == "red_rune.welcome_pilgrim"
