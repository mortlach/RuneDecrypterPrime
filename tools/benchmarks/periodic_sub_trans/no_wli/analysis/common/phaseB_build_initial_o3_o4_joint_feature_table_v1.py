from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_joint_feature_contract_v1 import (
    JointFeatureRow,
    sample_key,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_joint_rule_grid_reference_v1 import (
    classify_phrase_confidence,
    rule_flags,
)

O3_REQUIRED = {"chunk_id", "source_kind", "model_name", "damage_level", "repeat_index"}
O4_REQUIRED = {"chunk_id", "source_kind", "model_name", "damage_level", "repeat_index"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_rows(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def f(row: Mapping[str, Any], key: str) -> float:
    text = str(row.get(key, "") or "0").strip()
    return float(text) if text else 0.0


def i(row: Mapping[str, Any], key: str) -> int:
    text = str(row.get(key, "") or "0").strip()
    return int(float(text)) if text else 0


def build_joint_rows(o3_rows: list[Mapping[str, Any]], o4_rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    # O3 rows may be one row per lens. Collapse by sample key.
    o3_by_key: dict[str, dict[str, Any]] = {}
    for row in o3_rows:
        key = sample_key(row)
        target = o3_by_key.setdefault(key, dict(row))
        lens = str(row.get("lens_name", ""))
        value = f(row, "selected_nonoverlap_exact_weight") or f(row, "selected_weight") or f(row, "score")
        if lens == "HD0_L10":
            target["o3_hd0_l10_weight"] = max(f(target, "o3_hd0_l10_weight"), value)
        elif lens == "HD0_L12":
            target["o3_hd0_l12_weight"] = max(f(target, "o3_hd0_l12_weight"), value)
        elif lens in {"HDle1_L12", "HD1_L12"}:
            target["o3_hdle1_l12_weight"] = max(f(target, "o3_hdle1_l12_weight"), value)
        elif lens in {"HDle2_L15", "HD2_L15"}:
            target["o3_hdle2_l15_weight"] = max(f(target, "o3_hdle2_l15_weight"), value)
        target["o3_longest_exact_phrase_len"] = max(i(target, "o3_longest_exact_phrase_len"), i(row, "longest_exact_phrase_len"))

    o4_by_key: dict[str, Mapping[str, Any]] = {sample_key(row): row for row in o4_rows}
    out: list[dict[str, Any]] = []
    for key, o3 in sorted(o3_by_key.items()):
        o4 = o4_by_key.get(key, {})
        base = JointFeatureRow(
            sample_key=key,
            chunk_id=str(o3.get("chunk_id", o4.get("chunk_id", ""))),
            source_kind=str(o3.get("source_kind", o4.get("source_kind", ""))),
            model_name=str(o3.get("model_name", o4.get("model_name", ""))),
            damage_level=str(o3.get("damage_level", o4.get("damage_level", ""))),
            repeat_index=str(o3.get("repeat_index", o4.get("repeat_index", ""))),
            changed_fraction=f(o3, "changed_fraction") or f(o4, "changed_fraction"),
            null_class=str(o3.get("null_class", o4.get("null_class", ""))),
            o3_hd0_l10_weight=f(o3, "o3_hd0_l10_weight"),
            o3_hd0_l12_weight=f(o3, "o3_hd0_l12_weight"),
            o3_hdle1_l12_weight=f(o3, "o3_hdle1_l12_weight"),
            o3_hdle2_l15_weight=f(o3, "o3_hdle2_l15_weight"),
            o3_longest_exact_phrase_len=i(o3, "o3_longest_exact_phrase_len"),
            o4_exact_hit_count=i(o4, "exact_hit_count"),
            o4_longest_exact_phrase_len=i(o4, "longest_exact_phrase_len"),
            o4_selected_nonoverlap_exact_count=i(o4, "selected_nonoverlap_exact_count"),
            o4_selected_nonoverlap_exact_weight=f(o4, "selected_nonoverlap_exact_weight"),
        ).row()
        base["phrase_confidence_class"] = classify_phrase_confidence(base)
        base.update({name: int(value) for name, value in rule_flags(base).items()})
        out.append(base)
    return out


def main() -> None:
    # Edit these local paths after wiring into RDP. Kept simple/IDE-friendly.
    base = Path("output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_strict_o3_o4_fwd_initial_joint_diagnostic_v1")
    o3_path = base / "input_o3_anchor_summary_rows.csv"
    o4_path = base / "input_o4_summary_rows.csv"
    out_path = base / "joint_feature_rows.csv"
    rows = build_joint_rows(read_rows(o3_path), read_rows(o4_path))
    write_rows(out_path, rows)
    (base / "run_manifest.json").write_text(json.dumps({"status": "complete", "joint_rows": len(rows)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
