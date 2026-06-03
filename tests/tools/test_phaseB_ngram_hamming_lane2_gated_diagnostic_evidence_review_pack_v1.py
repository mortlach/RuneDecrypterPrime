from __future__ import annotations

import csv
import json
from pathlib import Path
from zipfile import ZipFile

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1 as pack,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def seed_required_files(root: Path) -> None:
    for rel in (
        *pack.CONTEXT_FILES_REL,
        *pack.SOURCE_FILES_REL,
        *pack.TEST_FILES_REL,
        *pack.ASSET_INDEX_FILES_REL,
    ):
        write_text(root / rel)
    evidence = root / pack.EVIDENCE_DIR_REL
    write_json(
        evidence / "run_manifest.json",
        {
            "phase": "phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1",
            "run_authority": "diagnostic_only",
            "controlled_eval_corpus_scan_started": True,
            "real_candidate_scan_started": False,
            "broad_candidate_scan_started": False,
            "production_scorer_change": False,
            "lane1_asset_id": "phaseB_ngram_hamming_full_raw_v1",
            "phrase_entry_count": 4,
            "raw_hit_count": 10,
        },
    )
    write_json(evidence / "corpus_manifest.json", {"case_count": 8, "case_families": ["positive_clean"]})
    for rel in pack.COMPONENT_FILES_REL:
        path = root / rel
        if path.name.endswith(".json") and not path.exists():
            write_json(path, {"ok": True})
        elif path.suffix == ".csv":
            write_csv(path, [{"a": 1}])
        elif path.suffix == ".jsonl":
            write_text(path, "{}\n")
        elif not path.exists():
            write_text(path)


def test_review_pack_enforces_safe_state_and_includes_source_closure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    seed_required_files(tmp_path)

    manifest = pack.build_lane2_gated_diagnostic_evidence_review_pack(
        pack_dir=tmp_path / "planning/projects/no_wli/40_review_summaries/pack",
        zip_path=tmp_path / "planning/projects/no_wli/40_review_summaries/pack.zip",
    )

    assert manifest["status"] == "packed_review_ready"
    assert manifest["safe_state"] is True
    assert manifest["missing_files"] == []
    assert manifest["backslash_entries"] == 0
    assert "src/rune_decrypter_prime/scoring/ngram_hamming/reference.py" in pack.SOURCE_FILES_REL
    assert "src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py" in pack.SOURCE_FILES_REL
    assert "src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py" in pack.SOURCE_FILES_REL
    assert (
        "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py"
    ) in pack.SOURCE_FILES_REL


def test_review_pack_blocks_if_real_scan_or_production_change_is_present(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    seed_required_files(tmp_path)
    run_manifest = tmp_path / pack.EVIDENCE_DIR_REL / "run_manifest.json"
    payload = json.loads(run_manifest.read_text(encoding="utf-8"))
    payload["real_candidate_scan_started"] = True
    write_json(run_manifest, payload)

    manifest = pack.build_lane2_gated_diagnostic_evidence_review_pack(
        pack_dir=tmp_path / "planning/projects/no_wli/40_review_summaries/pack",
        zip_path=tmp_path / "planning/projects/no_wli/40_review_summaries/pack.zip",
    )

    assert manifest["status"] == "packed_with_blocks"
    assert manifest["safe_state"] is False


def test_review_pack_zip_is_self_contained_for_listed_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    seed_required_files(tmp_path)
    zip_path = tmp_path / "planning/projects/no_wli/40_review_summaries/pack.zip"

    manifest = pack.build_lane2_gated_diagnostic_evidence_review_pack(
        pack_dir=tmp_path / "planning/projects/no_wli/40_review_summaries/pack",
        zip_path=zip_path,
    )

    with ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
    assert manifest["entry_count"] > 0
    assert any(name.endswith("30_source/src/rune_decrypter_prime/scoring/ngram_hamming/reference.py") for name in names)
    assert any(
        name.endswith(
            "30_source/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py"
        )
        for name in names
    )
    assert any(name.endswith("50_asset_index/assets/ngram_hamming/phaseB_full_raw_v1/asset_manifest.json") for name in names)
