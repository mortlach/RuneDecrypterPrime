from __future__ import annotations

from typing import Any, Mapping


def as_float(row: Mapping[str, Any], key: str) -> float:
    text = str(row.get(key, "") or "0").strip()
    return float(text) if text else 0.0


def as_int(row: Mapping[str, Any], key: str) -> int:
    text = str(row.get(key, "") or "0").strip()
    return int(float(text)) if text else 0


def classify_phrase_confidence(row: Mapping[str, Any]) -> str:
    o3_l10 = as_float(row, "o3_hd0_l10_weight")
    o3_l12 = as_float(row, "o3_hd0_l12_weight")
    o4_weight = as_float(row, "o4_selected_nonoverlap_exact_weight")
    o4_count = as_int(row, "o4_selected_nonoverlap_exact_count")
    longest_o3 = as_int(row, "o3_longest_exact_phrase_len")
    longest_o4 = as_int(row, "o4_longest_exact_phrase_len")

    if o3_l10 >= 30.0 and (o4_weight > 0.0 or o4_count > 0 or longest_o4 >= 10):
        return "strong_confirm"
    if o3_l10 >= 30.0 or (o3_l12 >= 15.0 and o4_weight > 0.0):
        return "weak_confirm"
    if o3_l10 <= 0.0 and o4_weight > 0.0:
        return "inspect_o4_only"
    if longest_o3 >= 15 or longest_o4 >= 12:
        return "local_anchor_present"
    return "neutral"


def rule_flags(row: Mapping[str, Any]) -> dict[str, bool]:
    o3_l10 = as_float(row, "o3_hd0_l10_weight")
    o3_l12 = as_float(row, "o3_hd0_l12_weight")
    o4_weight = as_float(row, "o4_selected_nonoverlap_exact_weight")
    o4_exact = as_int(row, "o4_exact_hit_count")
    longest_o3 = as_int(row, "o3_longest_exact_phrase_len")
    longest_o4 = as_int(row, "o4_longest_exact_phrase_len")
    return {
        "rule_a_o3_l10_ge30": o3_l10 >= 30.0,
        "rule_b_o3_l10_ge20_o4_present": o3_l10 >= 20.0 and (o4_weight > 0.0 or o4_exact > 0),
        "rule_c_o3_l12_ge10_o4_present": o3_l12 >= 10.0 and (o4_weight > 0.0 or o4_exact > 0),
        "rule_d_longest_exact_ge15": max(longest_o3, longest_o4) >= 15,
    }
