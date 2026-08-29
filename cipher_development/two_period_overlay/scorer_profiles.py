from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from cipher_development.two_period_overlay.config import SCORING_CONTRACT

_ALLOWED_ORDERS = frozenset({1, 2, 3, 4})


@dataclass(frozen=True, slots=True)
class ScorerProfile:
    profile_id: str
    label: str
    role: str
    char_orders: tuple[int, ...]
    wli_orders: tuple[int, ...]
    char_family_weight: float
    wli_family_weight: float
    exact_recorded_contract: bool = False

    def __post_init__(self) -> None:
        if not self.profile_id or not self.profile_id.replace("_", "").isalnum():
            raise ValueError(
                "profile_id must be a compact alphanumeric/underscore identifier"
            )
        for field_name, raw_orders in (
            ("char_orders", self.char_orders),
            ("wli_orders", self.wli_orders),
        ):
            orders = tuple((int(value) for value in raw_orders))
            if len(set(orders)) != len(orders) or tuple(sorted(orders)) != orders:
                raise ValueError(f"{field_name} must be unique and sorted")
            if any((order not in _ALLOWED_ORDERS for order in orders)):
                raise ValueError(f"{field_name} must use only n-gram orders 1-4")
            object.__setattr__(self, field_name, orders)
        if not self.char_orders and (not self.wli_orders):
            raise ValueError("a scorer profile must activate at least one family")
        for field_name in ("char_family_weight", "wli_family_weight"):
            value = float(getattr(self, field_name))
            if value < 0.0:
                raise ValueError(f"{field_name} must be non-negative")
            object.__setattr__(self, field_name, value)
        if not self.char_orders and self.char_family_weight != 0.0:
            raise ValueError(
                "char-only weight must be zero when no character orders are active"
            )
        if not self.wli_orders and self.wli_family_weight != 0.0:
            raise ValueError("WLI weight must be zero when no WLI orders are active")
        if self.char_family_weight + self.wli_family_weight <= 0.0:
            raise ValueError("active family weights must sum to a positive value")

    @property
    def score_name(self) -> str:
        return f"profile_score__{self.profile_id}"

    def scoring_contract(self) -> dict[str, Any]:
        if self.exact_recorded_contract:
            return _copy_contract(SCORING_CONTRACT)
        contract = _copy_contract(SCORING_CONTRACT)
        total = self.char_family_weight + self.wli_family_weight
        char_family = self.char_family_weight / total
        wli_family = self.wli_family_weight / total
        contract.update(
            {
                "include_char": bool(self.char_orders),
                "use_word_breaks": bool(self.wli_orders),
                "n_char": max(self.char_orders, default=1),
                "n_wli": max(self.wli_orders, default=1),
                "weights": [char_family, wli_family],
                "char_weights": _equal_order_weights(self.char_orders, char_family),
                "wli_weights": _equal_order_weights(self.wli_orders, wli_family),
            }
        )
        return contract

    def to_json_dict(self) -> dict[str, Any]:
        contract = self.scoring_contract()
        return {
            "profile_id": self.profile_id,
            "label": self.label,
            "role": self.role,
            "char_orders": list(self.char_orders),
            "wli_orders": list(self.wli_orders),
            "declared_family_weights": {
                "character": self.char_family_weight,
                "wli": self.wli_family_weight,
            },
            "effective_family_weights": effective_family_weights(contract),
            "score_name": self.score_name,
            "exact_recorded_contract": self.exact_recorded_contract,
            "scoring_contract": portable_contract(contract),
        }


def _copy_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for key, value in contract.items():
        if isinstance(value, Mapping):
            copied[str(key)] = {int(k): float(v) for k, v in value.items()}
        elif isinstance(value, list):
            copied[str(key)] = list(value)
        else:
            copied[str(key)] = value
    return copied


def _equal_order_weights(
    orders: tuple[int, ...], family_total: float
) -> dict[int, float]:
    if not orders:
        return {}
    each = float(family_total) / len(orders)
    return {order: each for order in orders}


def effective_family_weights(contract: Mapping[str, Any]) -> dict[str, float]:
    char_map = contract.get("char_weights")
    wli_map = contract.get("wli_weights")
    char_total = 0.0
    wli_total = 0.0
    if bool(contract.get("include_char")) and isinstance(char_map, Mapping):
        char_total = sum((max(0.0, float(value)) for value in char_map.values()))
    if bool(contract.get("use_word_breaks")) and isinstance(wli_map, Mapping):
        wli_total = sum((max(0.0, float(value)) for value in wli_map.values()))
    total = char_total + wli_total
    if total <= 0.0:
        raise ValueError("scoring contract has no active per-order model weight")
    return {"character": char_total / total, "wli": wli_total / total}


def portable_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in contract.items():
        if isinstance(value, Mapping):
            out[str(key)] = {str(k): v for k, v in value.items()}
        elif isinstance(value, tuple):
            out[str(key)] = list(value)
        else:
            out[str(key)] = value
    return out


RECORDED_J0 = ScorerProfile(
    "j0_recorded_char34_wli34",
    "J0 recorded baseline",
    "baseline",
    (3, 4),
    (3, 4),
    0.25,
    0.75,
    exact_recorded_contract=True,
)
S1 = ScorerProfile("s1_char12", "S1 char12", "scout", (1, 2), (), 1.0, 0.0)
S2 = ScorerProfile("s2_wli12", "S2 WLI12", "scout", (), (1, 2), 0.0, 1.0)
S3 = ScorerProfile(
    "s3_char12_wli12", "S3 char12 + WLI12", "scout", (1, 2), (1, 2), 0.25, 0.75
)
B1 = ScorerProfile(
    "b1_char23_wli23", "B1 char23 + WLI23", "bridge", (2, 3), (2, 3), 0.25, 0.75
)
J1 = ScorerProfile(
    "j1_char34_wli34", "J1 char34 + WLI34", "judge", (3, 4), (3, 4), 0.25, 0.75
)
F1 = ScorerProfile(
    "f1_char1234_wli1234",
    "F1 char1234 + WLI1234",
    "complete_multiscale",
    (1, 2, 3, 4),
    (1, 2, 3, 4),
    0.25,
    0.75,
)
SCORER_PANEL = (RECORDED_J0, S1, S2, S3, B1, J1, F1)
SCORER_PROFILES = {profile.profile_id: profile for profile in SCORER_PANEL}


def profile_for(profile_id: str) -> ScorerProfile:
    try:
        return SCORER_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"unknown scorer profile {profile_id!r}") from exc


def weighting_contract_note() -> dict[str, Any]:
    return {
        "affected_item": "WP6 C.5 initial family weighting and fixed high-order baseline",
        "evidence": "The current NumPy and Torch scorer runtimes globally normalise per-order maps and consult the pair weights only when those maps are absent.",
        "recorded_baseline_effective_weights": effective_family_weights(
            RECORDED_J0.scoring_contract()
        ),
        "intended_combined_profile_effective_weights": effective_family_weights(
            J1.scoring_contract()
        ),
        "replacement_action": "Preserve the exact recorded baseline as J0, encode 0.25/0.75 directly in campaign-local per-order maps for S3/B1/J1/F1, and do not alter core scorer runtime.",
    }


__all__ = [
    "B1",
    "F1",
    "J1",
    "RECORDED_J0",
    "S1",
    "S2",
    "S3",
    "SCORER_PANEL",
    "SCORER_PROFILES",
    "ScorerProfile",
    "effective_family_weights",
    "portable_contract",
    "profile_for",
    "weighting_contract_note",
]
