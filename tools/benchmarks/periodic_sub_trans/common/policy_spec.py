from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class AdaptivePolicySpec:
    policy_id: str
    tie_band_eps: float = 0.0
    ambiguity_expand_top_k: int = 0
    period_scale: Mapping[int, float] = field(default_factory=dict)
    columns_scale: Mapping[int, float] = field(default_factory=dict)
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.policy_id).strip():
            raise ValueError("AdaptivePolicySpec.policy_id must be non-empty")
        if float(self.tie_band_eps) < 0.0:
            raise ValueError("AdaptivePolicySpec.tie_band_eps must be >= 0")
        if int(self.ambiguity_expand_top_k) < 0:
            raise ValueError("AdaptivePolicySpec.ambiguity_expand_top_k must be >= 0")
        for k, v in dict(self.period_scale).items():
            if float(v) <= 0.0:
                raise ValueError(f"AdaptivePolicySpec.period_scale[{k}] must be > 0")
        for k, v in dict(self.columns_scale).items():
            if float(v) <= 0.0:
                raise ValueError(f"AdaptivePolicySpec.columns_scale[{k}] must be > 0")

    def scale_for(self, *, period: int, columns: int) -> float:
        p = float(self.period_scale.get(int(period), 1.0))
        c = float(self.columns_scale.get(int(columns), 1.0))
        return p * c

    def to_json_dict(self) -> dict[str, Any]:
        return dict(
            policy_id=str(self.policy_id),
            tie_band_eps=float(self.tie_band_eps),
            ambiguity_expand_top_k=int(self.ambiguity_expand_top_k),
            period_scale={str(k): float(self.period_scale[k]) for k in sorted(self.period_scale.keys(), key=lambda x: int(x))},
            columns_scale={str(k): float(self.columns_scale[k]) for k in sorted(self.columns_scale.keys(), key=lambda x: int(x))},
            params={str(k): self.params[k] for k in sorted(self.params.keys(), key=lambda x: str(x))},
        )

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "AdaptivePolicySpec":
        return cls(
            policy_id=str(payload.get("policy_id", "")),
            tie_band_eps=float(payload.get("tie_band_eps", 0.0)),
            ambiguity_expand_top_k=int(payload.get("ambiguity_expand_top_k", 0)),
            period_scale={int(k): float(v) for k, v in dict(payload.get("period_scale", {})).items()},
            columns_scale={int(k): float(v) for k, v in dict(payload.get("columns_scale", {})).items()},
            params=dict(payload.get("params", {})),
        )
