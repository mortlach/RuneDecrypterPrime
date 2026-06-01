from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    flatten_word_tokens,
    PhraseEntry,
    PhraseProfile,
    phrase_entry_from_asset_row,
    profile_allows_entry,
)


RUN_LABEL = "phaseB_ngram_hamming_full_raw_assets_summary_v1"
FULL_ASSET_ROOT_PARENT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_assets_v1"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_assets_summary_v1"
)
REQUIRED_DIRECTIONS = ("fwd",)
REQUIRED_CUTS = ("normal", "strict")
REQUIRED_ORDERS = (2, 3)
SCAN_MODE = "whole_phrase_only"
INTERNAL_PHRASE_WINDOWS = False
REQUIRED_PHRASE_INDEX_FIELDS = {
    "phrase_id",
    "direction",
    "dictionary_cut",
    "ngram_order",
    "word_token_ids",
    "rune_token_ids",
    "word_lengths",
    "phrase_token_length",
    "count",
    "sum_count",
    "max_count",
    "log_count",
    "max_log_count",
    "phrase_count",
    "top_latin_ngram",
    "top_latin_ngram_for_max_count",
}

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
    parent = REPO_ROOT / FULL_ASSET_ROOT_PARENT_REL
    candidates = [
        path
        for path in parent.iterdir()
        if path.is_dir() and (path / "full_raw_build_manifest.json").exists()
    ] if parent.exists() else []
    if not candidates:
        raise FileNotFoundError(f"no full raw asset build manifests under {FULL_ASSET_ROOT_PARENT_REL}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def validate_full_asset_root(asset_root: Path) -> dict[str, Any]:
    build_manifest_path = asset_root / "full_raw_build_manifest.json"
    config_path = asset_root / "config.json"
    if not build_manifest_path.exists():
        raise RuntimeError("missing full_raw_build_manifest.json")
    if not config_path.exists():
        raise RuntimeError("missing config.json")
    build_manifest = read_json(build_manifest_path)
    config = read_json(config_path)
    blocked: list[str] = []
    if build_manifest.get("asset_mode") != "full":
        blocked.append("asset_mode is not full")
    if build_manifest.get("full_asset_available") is not True:
        blocked.append("full_asset_available is not true")
    if build_manifest.get("full_raw_ngram_rebuild_confirmed") is not True:
        blocked.append("full_raw_ngram_rebuild_confirmed is not true")
    if build_manifest.get("sample_line_limit_per_order") is not None:
        blocked.append("build manifest contains sample_line_limit_per_order")
    if "sample_line_limit_per_order" in config and config.get("sample_line_limit_per_order") is not None:
        blocked.append("config contains non-null sample_line_limit_per_order")
    for cut in REQUIRED_CUTS:
        for direction in REQUIRED_DIRECTIONS:
            for order in REQUIRED_ORDERS:
                path = asset_root / f"{cut}_{direction}" / f"ngram{order}.csv.gz"
                if not path.exists():
                    blocked.append(f"missing expected asset file {repo_rel(path)}")
    return {
        "asset_root": repo_rel(asset_root),
        "blocked": bool(blocked),
        "blocked_reasons": blocked,
        "build_manifest": build_manifest,
        "config": config,
    }


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


def _asset_row_top_latin(row: dict[str, Any]) -> str:
    return str(row.get("top_latin_ngram", "") or row.get("latin_examples", "") or "")


def add_collapsed_entry(
    collapsed: dict[tuple[str, str, int, tuple[tuple[int, ...], ...]], dict[str, Any]],
    entry: PhraseEntry,
    row: dict[str, Any],
) -> None:
    identity = phrase_identity(entry)
    existing = collapsed.get(identity)
    count = float(entry.count)
    log_count = float(entry.log_count)
    phrase_count = int(entry.phrase_count)
    top_latin = _asset_row_top_latin(row)
    if existing is None:
        collapsed[identity] = {
            "entry": PhraseEntry(
                phrase_id=phrase_id_for_identity(identity),
                direction=entry.direction,
                dictionary_cut=entry.dictionary_cut,
                ngram_order=entry.ngram_order,
                word_token_ids=entry.word_token_ids,
                rune_token_ids=entry.rune_token_ids,
                count=count,
                log_count=log_count,
                phrase_count=phrase_count,
                top_latin_ngram=top_latin,
            ),
            "sum_count": count,
            "max_count": count,
            "max_log_count": log_count,
            "phrase_count": phrase_count,
            "top_latin_ngram_for_max_count": top_latin,
            "duplicate_row_count": 0,
        }
        return
    existing["sum_count"] = float(existing["sum_count"]) + count
    existing["phrase_count"] = int(existing["phrase_count"]) + phrase_count
    existing["duplicate_row_count"] = int(existing["duplicate_row_count"]) + 1
    if count > float(existing["max_count"]):
        existing["max_count"] = count
        existing["max_log_count"] = log_count
        existing["top_latin_ngram_for_max_count"] = top_latin
    existing_entry = existing["entry"]
    existing["entry"] = PhraseEntry(
        phrase_id=existing_entry.phrase_id,
        direction=existing_entry.direction,
        dictionary_cut=existing_entry.dictionary_cut,
        ngram_order=existing_entry.ngram_order,
        word_token_ids=existing_entry.word_token_ids,
        rune_token_ids=existing_entry.rune_token_ids,
        count=float(existing["sum_count"]),
        log_count=math.log1p(float(existing["sum_count"])),
        phrase_count=int(existing["phrase_count"]),
        top_latin_ngram=str(existing["top_latin_ngram_for_max_count"]),
    )


def collapsed_to_json(row: dict[str, Any]) -> dict[str, Any]:
    entry = row["entry"]
    payload = entry_to_json(entry)
    payload["count"] = float(row["sum_count"])
    payload["sum_count"] = float(row["sum_count"])
    payload["max_count"] = float(row["max_count"])
    payload["log_count"] = math.log1p(float(row["sum_count"]))
    payload["max_log_count"] = float(row["max_log_count"])
    payload["phrase_count"] = int(row["phrase_count"])
    payload["top_latin_ngram"] = str(row["top_latin_ngram_for_max_count"])
    payload["top_latin_ngram_for_max_count"] = str(row["top_latin_ngram_for_max_count"])
    payload["duplicate_row_count"] = int(row["duplicate_row_count"])
    return payload


def load_entries(asset_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    collapsed: dict[tuple[str, str, int, tuple[tuple[int, ...], ...]], dict[str, Any]] = {}
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
                        add_collapsed_entry(collapsed, entry, row)
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
                        "collapsed_duplicate_identity_rows": sum(
                            int(item["duplicate_row_count"])
                            for identity, item in collapsed.items()
                            if identity[1] == cut and identity[0] == direction and identity[2] == order
                        ),
                        "status": "pass" if raw_rows > 0 and invalid_rows == 0 else "blocked",
                    }
                )
    phrase_rows = [collapsed_to_json(row) for row in collapsed.values()]
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


def validate_phrase_index_row(row: dict[str, Any], row_number: int) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_PHRASE_INDEX_FIELDS - set(row))
    if missing:
        errors.append(f"row {row_number}: missing fields {', '.join(missing)}")
        return errors
    word_token_ids = row["word_token_ids"]
    rune_token_ids = row["rune_token_ids"]
    word_lengths = row["word_lengths"]
    errors.extend(validate_word_token_ids(word_token_ids, row_number))
    errors.extend(validate_flat_token_ids(rune_token_ids, row_number, "rune_token_ids"))
    errors.extend(validate_word_lengths(word_lengths, row_number))
    errors.extend(validate_int_field(row.get("phrase_token_length"), row_number, "phrase_token_length", positive=True))
    errors.extend(validate_int_field(row.get("ngram_order"), row_number, "ngram_order", positive=True))
    errors.extend(validate_numeric_field(row.get("count"), row_number, "count", non_negative=True))
    errors.extend(validate_numeric_field(row.get("sum_count"), row_number, "sum_count", non_negative=True))
    errors.extend(validate_numeric_field(row.get("max_count"), row_number, "max_count", non_negative=True))
    errors.extend(validate_numeric_field(row.get("log_count"), row_number, "log_count", non_negative=True))
    errors.extend(validate_numeric_field(row.get("max_log_count"), row_number, "max_log_count", non_negative=True))
    errors.extend(validate_int_field(row.get("phrase_count"), row_number, "phrase_count", positive=True))
    if errors:
        return errors
    word_token_ids = tuple(tuple(token for token in word) for word in word_token_ids)
    rune_token_ids = tuple(token for token in rune_token_ids)
    word_lengths = tuple(length for length in word_lengths)
    phrase_token_length = row["phrase_token_length"]
    ngram_order = row["ngram_order"]
    if len(rune_token_ids) != phrase_token_length:
        errors.append(f"row {row_number}: phrase_token_length != len(rune_token_ids)")
    if tuple(len(word) for word in word_token_ids) != word_lengths:
        errors.append(f"row {row_number}: word_lengths != lengths of word_token_ids")
    if sum(word_lengths) != phrase_token_length:
        errors.append(f"row {row_number}: sum(word_lengths) != phrase_token_length")
    if flatten_word_tokens(word_token_ids) != rune_token_ids:
        errors.append(f"row {row_number}: flatten(word_token_ids) != rune_token_ids")
    if ngram_order != len(word_token_ids):
        errors.append(f"row {row_number}: ngram_order != len(word_token_ids)")
    if row["direction"] not in REQUIRED_DIRECTIONS:
        errors.append(f"row {row_number}: direction outside required set")
    if row["dictionary_cut"] not in REQUIRED_CUTS:
        errors.append(f"row {row_number}: dictionary_cut outside required set")
    if ngram_order not in REQUIRED_ORDERS:
        errors.append(f"row {row_number}: ngram_order outside required set")
    return errors


def validate_int_field(value: Any, row_number: int, field_name: str, *, positive: bool) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int):
        return [f"row {row_number}: {field_name} must be an integer"]
    if positive and value <= 0:
        return [f"row {row_number}: {field_name} must be positive"]
    return []


def validate_numeric_field(value: Any, row_number: int, field_name: str, *, non_negative: bool) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return [f"row {row_number}: {field_name} must be numeric"]
    if not math.isfinite(float(value)):
        return [f"row {row_number}: {field_name} must be finite"]
    if non_negative and float(value) < 0:
        return [f"row {row_number}: {field_name} must be non-negative"]
    return []


def validate_flat_token_ids(values: Any, row_number: int, field_name: str) -> list[str]:
    if not isinstance(values, list) or not values:
        return [f"row {row_number}: {field_name} is empty or not a list"]
    for token in values:
        if isinstance(token, bool) or not isinstance(token, int):
            return [f"row {row_number}: {field_name} contains non-integer token"]
        if token < 0 or token > 28:
            return [f"row {row_number}: {field_name} token outside 0..28"]
    return []


def validate_word_token_ids(words: Any, row_number: int) -> list[str]:
    if not isinstance(words, list) or not words:
        return [f"row {row_number}: word_token_ids is empty or not a list"]
    for word in words:
        if not isinstance(word, list) or not word:
            return [f"row {row_number}: word_token_ids contains empty/non-list word"]
        errors = validate_flat_token_ids(word, row_number, "word_token_ids")
        if errors:
            return errors
    return []


def validate_word_lengths(lengths: Any, row_number: int) -> list[str]:
    if not isinstance(lengths, list) or not lengths:
        return [f"row {row_number}: word_lengths is empty or not a list"]
    for length in lengths:
        if isinstance(length, bool) or not isinstance(length, int):
            return [f"row {row_number}: word_lengths contains non-integer value"]
        if length <= 0:
            return [f"row {row_number}: word_lengths contains non-positive value"]
    return []


def validate_phrase_rows(phrase_rows: list[dict[str, Any]]) -> dict[str, Any]:
    invalid_examples: list[str] = []
    invalid_count = 0
    for index, row in enumerate(phrase_rows, start=1):
        errors = validate_phrase_index_row(row, index)
        if errors:
            invalid_count += 1
            invalid_examples.extend(errors[:3])
            invalid_examples = invalid_examples[:20]
    return {
        "phrase_index_rows_checked": len(phrase_rows),
        "phrase_index_invalid_row_count": invalid_count,
        "phrase_index_invalid_examples": invalid_examples,
    }


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
                    scoped_profile = PhraseProfile(
                        profile_id=profile.profile_id,
                        direction=direction,
                        orders=(order,),
                        dictionary_cuts=(cut,),
                        min_phrase_token_length=profile.min_phrase_token_length,
                        max_total_phrase_hd=profile.max_total_phrase_hd,
                        max_word_hd=profile.max_word_hd,
                        normalised_hd_ceiling=profile.normalised_hd_ceiling,
                        exact_match_word_lengths=profile.exact_match_word_lengths,
                    )
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
    path = output_dir / "phrase_index_full_raw_order2_order3_fwd.jsonl.gz"
    ensure_under_repo(path)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in phrase_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return repo_rel(path), sha256_file(path)


def summarise_full_raw_assets(asset_root: Path | None = None) -> dict[str, Any]:
    selected_root = asset_root or latest_asset_root()
    gate = validate_full_asset_root(selected_root)
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    phrase_rows: list[dict[str, Any]] = []
    asset_rows: list[dict[str, Any]] = []
    pattern_rows: list[dict[str, Any]] = []
    eligibility_rows: list[dict[str, Any]] = []
    phrase_index_path = ""
    phrase_index_sha256 = ""
    phrase_validation = {
        "phrase_index_rows_checked": 0,
        "phrase_index_invalid_row_count": 0,
        "phrase_index_invalid_examples": [],
    }
    if not gate["blocked"]:
        phrase_rows, asset_rows, pattern_rows = load_entries(selected_root)
        phrase_validation = validate_phrase_rows(phrase_rows)
        eligibility_rows = profile_eligibility_rows(phrase_rows)
        phrase_index_path, phrase_index_sha256 = write_phrase_index(phrase_rows, output_dir)
    blocked = list(gate["blocked_reasons"])
    if phrase_validation["phrase_index_invalid_row_count"]:
        blocked.append("phrase index validation found invalid rows")
    if asset_rows and any(row["status"] != "pass" for row in asset_rows):
        blocked.extend(f"asset validation failed for {row['asset_path']}" for row in asset_rows if row["status"] != "pass")
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not blocked and phrase_rows else "blocked",
        "blocked_reasons": blocked,
        "asset_mode": "full",
        "full_asset_available": True,
        "full_raw_ngram_rebuild_confirmed": not blocked and bool(phrase_rows),
        "sample_line_limit_per_order": None,
        "sample_line_limit_per_order_present": False,
        "scan_mode": SCAN_MODE,
        "internal_phrase_windows": INTERNAL_PHRASE_WINDOWS,
        "asset_root": repo_rel(selected_root),
        "source_raw_ngram_root_name": gate["build_manifest"].get("source_raw_ngram_root_name", ""),
        "dictionary_dirs_by_cut": posixish(gate["build_manifest"].get("dictionary_dirs_by_cut", {})),
        "required_directions": list(REQUIRED_DIRECTIONS),
        "required_cuts": list(REQUIRED_CUTS),
        "required_orders": list(REQUIRED_ORDERS),
        "phrase_entry_count": len(phrase_rows),
        "phrase_index_path": phrase_index_path,
        "phrase_index_sha256": phrase_index_sha256,
        **phrase_validation,
        "profiles": [asdict(profile) for profile in PROFILES],
    }
    write_json(output_dir / "full_raw_asset_summary_manifest.json", manifest)
    write_csv(output_dir / "full_raw_asset_file_rows.csv", asset_rows)
    write_csv(output_dir / "full_raw_profile_eligibility_rows.csv", eligibility_rows)
    write_csv(output_dir / "full_raw_word_length_pattern_rows.csv", pattern_rows)
    readout = [
        "# PhaseB N-Gram Hamming Full Raw Assets Summary v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- asset mode: `{manifest['asset_mode']}`",
        f"- full raw confirmed: `{manifest['full_raw_ngram_rebuild_confirmed']}`",
        f"- sample line limit per order: `{manifest['sample_line_limit_per_order']}`",
        f"- phrase entries: `{manifest['phrase_entry_count']}`",
        f"- phrase index SHA256: `{manifest['phrase_index_sha256']}`",
        f"- scan mode for upcoming matrix: `{SCAN_MODE}`",
        f"- internal phrase windows: `{INTERNAL_PHRASE_WINDOWS}`",
        "",
        "P2/P3 are whole-phrase evidence with a minimum length gate, not fixed-length 8-rune evidence.",
        "P3 eligible phrase counts may equal P2 because P3's short-word guard is enforced at hit verification time.",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] phrase_entries={manifest['phrase_entry_count']}")
    return manifest


def main() -> None:
    summarise_full_raw_assets()


if __name__ == "__main__":
    main()
