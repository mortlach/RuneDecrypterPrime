from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping

JOIN_KEYS = ("chunk_id", "source_kind", "model_name", "damage_level", "repeat_index")


@dataclass(frozen=True)
class JointFeatureRow:
    sample_key: str
    chunk_id: str
    source_kind: str
    model_name: str
    damage_level: str
    repeat_index: str
    changed_fraction: float
    null_class: str
    o3_hd0_l10_weight: float = 0.0
    o3_hd0_l12_weight: float = 0.0
    o3_hdle1_l12_weight: float = 0.0
    o3_hdle2_l15_weight: float = 0.0
    o3_longest_exact_phrase_len: int = 0
    o4_exact_hit_count: int = 0
    o4_longest_exact_phrase_len: int = 0
    o4_selected_nonoverlap_exact_count: int = 0
    o4_selected_nonoverlap_exact_weight: float = 0.0

    @property
    def joint_class(self) -> str:
        o3 = max(self.o3_hd0_l10_weight, self.o3_hd0_l12_weight) > 0.0
        o4 = self.o4_selected_nonoverlap_exact_weight > 0.0 or self.o4_exact_hit_count > 0
        if o3 and o4:
            return "O3_plus_O4"
        if o3:
            return "O3_only"
        if o4:
            return "O4_only"
        return "neither"

    def row(self) -> dict[str, Any]:
        out = asdict(self)
        out["joint_class"] = self.joint_class
        return out


def sample_key(row: Mapping[str, Any]) -> str:
    parts = [str(row.get(key, "")) for key in JOIN_KEYS]
    return "|".join(parts)
