from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    PhraseEntry,
    PhraseProfile,
    phrase_entry_from_asset_row,
    profile_allows_entry,
)


RUN_LABEL = "phaseB_ngram_hamming_canary_probe_assets_summary_v1"
ASSET_ROOT_PARENT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_canary_probe_assets_v1"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_canary_probe_assets_summary_v1"
)

ASSET_MODE = "canary_probe"
REQUIRED_DIRECTIONS = ("fwd",)
REQUIRED_CUTS = ("normal", "strict")
REQUIRED_ORDERS = (2, 3)
SAMPLE_LINE_LIMIT_PER_ORDER = 25_000
SCAN_MODE = "whole_phrase_only"
INTERNAL_PHRASE_WINDOWS = False

PROFILES = (
    PhraseProfile(
        profile_id="P2_conservative_len8_hd2",
        direction="fwd",
        orders=REQUIRED_ORDERS,
        dictionary_cuts=REQUIRED_CUTS,
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
    ),
    PhraseProfile(
        profile_id="P3_word_shape_guarded_len8_hd2",
        direction="fwd",
        orders=REQUIRED_ORDERS,
        dictionary_cuts=REQUIRED_CUTS,
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
        exact_match_word_lengths=(1, 2),
    ),
)


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def posixish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): posixish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [posixish(item) for item in value]
    if isinstance(value, str):
        return value.replace("\\", "/")
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_asset_root() -> Path:
    parent = REPO_ROOT / ASSET_ROOT_PARENT_REL
    candidates = [
        path
        for path in parent.iterdir()
        if path.is_dir() and (path / "canary_probe_asset_manifest.json").exists()
    ] if parent.exists() else []
    if not candidates:
        raise FileNotFoundError(f"no canary probe asset manifest under {ASSET_ROOT_PARENT_REL}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def validate_probe_asset_root(asset_root: Path) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    manifest_path = asset_root / "canary_probe_asset_manifest.json"
    config_path = asset_root / "config.json"
    if not manifest_path.exists():
        raise RuntimeError("missing canary_probe_asset_manifest.json")
    if not config_path.exists():
        raise RuntimeError("missing config.json")
    manifest = read_json(manifest_path)
    config = read_json(config_path)
    blocked: list[str] = []
    if manifest.get("asset_mode") != ASSET_MODE:
        blocked.append("asset_mode is not canary_probe")
    if manifest.get("full_asset_available") is not False:
        blocked.append("probe full_asset_available must be false")
    if manifest.get("full_raw_ngram_rebuild_confirmed") is not False:
        blocked.append("probe full_raw_ngram_rebuild_confirmed must be false")
    if manifest.get("sample_line_limit_per_order") != SAMPLE_LINE_LIMIT_PER_ORDER:
        blocked.append("sample_line_limit_per_order does not match probe cap")
    if config.get("sample_line_limit_per_order") != SAMPLE_LINE_LIMIT_PER_ORDER:
        blocked.append("config sample_line_limit_per_order does not match probe cap")
    for cut in REQUIRED_CUTS:
        for direction in REQUIRED_DIRECTIONS:
            for order in REQUIRED_ORDERS:
                path = asset_root / f"{cut}_{direction}" / f"ngram{order}.csv.gz"
                if not path.exists():
                    blocked.append(f"missing expected probe asset file {repo_rel(path)}")
    return manifest, config, blocked


def phrase_identity(entry: PhraseEntry) -> tuple[str, str, int, tuple[tuple[int, ...], ...]]:
    return (entry.direction, entry.dictionary_cut, entry.ngram_order, entry.word_token_ids)


def phrase_id_for_identity(identity: tuple[str, str, int, tuple[tuple[int, ...], ...]]) -> str:
    direction, cut, order, words = identity
    return f"{direction}|{cut}|{order}|{json.dumps(words, separators=(',', ':'))}"


def entry_to_json(entry: PhraseEntry) -> dict[str, Any]:
    return {
        "phrase_id": entry.phrase_id,
        "direction": entry.direction,
        "dictionary_cut": entry.dictionary_cut,
        "ngram_order": entry.ngram_order,
        "word_token_ids": entry.word_token_ids,
        "rune_token_ids": entry.rune_token_ids,
        "word_lengths": entry.word_lengths,
        "phrase_token_length": entry.phrase_token_length,
        "count": entry.count,
        "sum_count": entry.count,
        "max_count": entry.count,
        "log_count": entry.log_count,
        "max_log_count": entry.log_count,
        "phrase_count": entry.phrase_count,
        "top_latin_ngram": entry.top_latin_ngram,
        "top_latin_ngram_for_max_count": entry.top_latin_ngram,
    }


def load_entries(asset_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    collapsed: dict[tuple[str, str, int, tuple[tuple[int, ...], ...]], PhraseEntry] = {}
    asset_rows: list[dict[str, Any]] = []
    word_pattern_counts: Counter[tuple[str, str, int, tuple[int, ...]]] = Counter()
    for cut in REQUIRED_CUTS:
        for direction in REQUIRED_DIRECTIONS:
            for order in REQUIRED_ORDERS:
                path = asset_root / f"{cut}_{direction}" / f"ngram{order}.csv.gz"
                raw_rows = 0
                invalid_rows = 0
                with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        raw_rows += 1
                        try:
                            entry = phrase_entry_from_asset_row(row)
                        except Exception:
                            invalid_rows += 1
                            continue
                        identity = phrase_identity(entry)
                        collapsed[identity] = replace(entry, phrase_id=phrase_id_for_identity(identity))
                        word_pattern_counts[(cut, direction, order, entry.word_lengths)] += 1
                asset_rows.append(
                    {
                        "asset_path": repo_rel(path),
                        "dictionary_cut": cut,
                        "direction": direction,
                        "ngram_order": order,
                        "raw_rows": raw_rows,
                        "invalid_rows": invalid_rows,
                        "phrase_entries": raw_rows - invalid_rows,
                        "status": "pass" if raw_rows > 0 and invalid_rows == 0 else "blocked",
                    }
                )
    phrase_rows = [entry_to_json(entry) for entry in collapsed.values()]
    phrase_rows.sort(key=lambda row: (row["direction"], row["dictionary_cut"], row["ngram_order"], row["phrase_id"]))
    pattern_rows = [
        {
            "dictionary_cut": cut,
            "direction": direction,
            "ngram_order": order,
            "word_lengths": json.dumps(list(lengths)),
            "phrase_entries": count,
        }
        for (cut, direction, order, lengths), count in sorted(word_pattern_counts.items())
    ]
    return phrase_rows, asset_rows, pattern_rows


def profile_eligibility_rows(phrase_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries = [
        PhraseEntry(
            phrase_id=row["phrase_id"],
            direction=row["direction"],
            dictionary_cut=row["dictionary_cut"],
            ngram_order=int(row["ngram_order"]),
            word_token_ids=tuple(tuple(int(token) for token in word) for word in row["word_token_ids"]),
            rune_token_ids=tuple(int(token) for token in row["rune_token_ids"]),
            count=float(row.get("count", 0.0) or 0.0),
            log_count=float(row.get("log_count", 0.0) or 0.0),
            phrase_count=int(row.get("phrase_count", 1) or 1),
        )
        for row in phrase_rows
    ]
    rows: list[dict[str, Any]] = []
    for profile in PROFILES:
        for cut in REQUIRED_CUTS:
            for direction in REQUIRED_DIRECTIONS:
                for order in REQUIRED_ORDERS:
                    scoped_profile = replace(profile, direction=direction, orders=(order,), dictionary_cuts=(cut,))
                    eligible = [entry for entry in entries if profile_allows_entry(entry, scoped_profile)]
                    rows.append(
                        {
                            "profile_id": profile.profile_id,
                            "dictionary_cut": cut,
                            "direction": direction,
                            "ngram_order": order,
                            "eligible_phrase_entries": len(eligible),
                            "min_phrase_token_length": min((entry.phrase_token_length for entry in eligible), default=0),
                            "max_phrase_token_length": max((entry.phrase_token_length for entry in eligible), default=0),
                            "exact_match_word_lengths": json.dumps(list(profile.exact_match_word_lengths)),
                        }
                    )
    return rows


def write_phrase_index(phrase_rows: list[dict[str, Any]], output_dir: Path) -> tuple[str, str]:
    path = output_dir / "phrase_index_canary_probe_order2_order3_fwd.jsonl.gz"
    ensure_under_repo(path)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in phrase_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return repo_rel(path), sha256_file(path)


def summarise_canary_probe_assets() -> dict[str, Any]:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "canary_probe_asset_summary_manifest.json")
    asset_root = latest_asset_root()
    asset_manifest, config, blocked = validate_probe_asset_root(asset_root)
    phrase_rows: list[dict[str, Any]] = []
    asset_rows: list[dict[str, Any]] = []
    pattern_rows: list[dict[str, Any]] = []
    eligibility_rows: list[dict[str, Any]] = []
    phrase_index_path = ""
    phrase_index_sha256 = ""
    if not blocked:
        phrase_rows, asset_rows, pattern_rows = load_entries(asset_root)
        eligibility_rows = profile_eligibility_rows(phrase_rows)
        phrase_index_path, phrase_index_sha256 = write_phrase_index(phrase_rows, output_dir)
    if asset_rows and any(row["status"] != "pass" for row in asset_rows):
        blocked.extend(f"probe asset validation failed for {row['asset_path']}" for row in asset_rows if row["status"] != "pass")
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not blocked and phrase_rows else "blocked",
        "blocked_reasons": blocked,
        "asset_mode": ASSET_MODE,
        "full_asset_available": False,
        "full_raw_ngram_rebuild_confirmed": False,
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "sample_line_limit_per_order_present": True,
        "scan_mode": SCAN_MODE,
        "internal_phrase_windows": INTERNAL_PHRASE_WINDOWS,
        "asset_root": repo_rel(asset_root),
        "source_raw_ngram_root_name": asset_manifest.get("source_raw_ngram_root_name", ""),
        "dictionary_dirs_by_cut": posixish(config.get("dictionary_dirs_by_cut", {})),
        "required_directions": list(REQUIRED_DIRECTIONS),
        "required_cuts": list(REQUIRED_CUTS),
        "required_orders": list(REQUIRED_ORDERS),
        "phrase_entry_count": len(phrase_rows),
        "phrase_index_path": phrase_index_path,
        "phrase_index_sha256": phrase_index_sha256,
        "profiles": [asdict(profile) for profile in PROFILES],
        "full_run_gate_expected_result": "blocked_as_expected_for_probe",
        "length_bias_warning": "P2/P3 len8 is a minimum whole-phrase token-length gate, not fixed-length 8-rune evidence.",
    }
    write_json(output_dir / "canary_probe_asset_summary_manifest.json", manifest)
    write_csv(output_dir / "canary_probe_asset_file_rows.csv", asset_rows)
    write_csv(output_dir / "canary_probe_profile_eligibility_rows.csv", eligibility_rows)
    write_csv(output_dir / "canary_probe_word_length_pattern_rows.csv", pattern_rows)
    readout = [
        "# PhaseB N-Gram Hamming Canary Probe Assets Summary v1",
        "",
        f"Status: `{manifest['status']}`",
        f"Asset mode: `{ASSET_MODE}`",
        f"Sample line limit per order: `{SAMPLE_LINE_LIMIT_PER_ORDER}`",
        f"Phrase entries: `{manifest['phrase_entry_count']}`",
        "",
        "This is a canary probe asset set, not a full raw asset set.",
        "A future full-run gate must reject it.",
        "",
        "Scan mode: `whole_phrase_only`; internal phrase windows: `false`.",
        "P2/P3 `len8` is a minimum whole-phrase token-length gate, not fixed-length 8-rune evidence.",
        "P3 eligible phrase counts may equal P2 because P3's short-word guard is enforced at hit verification time.",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")
    print(f"[{RUN_LABEL}] status={manifest['status']}", flush=True)
    print(f"[{RUN_LABEL}] phrase_entries={manifest['phrase_entry_count']}", flush=True)
    return manifest


def main() -> None:
    summarise_canary_probe_assets()


if __name__ == "__main__":
    main()
