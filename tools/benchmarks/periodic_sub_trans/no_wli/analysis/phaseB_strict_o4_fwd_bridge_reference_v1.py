from __future__ import annotations

"""
Strict O4 FWD bridge diagnostic reference helpers v1.

Report-only utilities for consuming the accepted O4 FWD NOSE runtime index.
This module is intentionally explicit and small: strict cut only, order 4 only,
FWD only, bounded diagnostics only.
"""

import csv
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

REQUIRED_DIRECTION = "fwd"
REQUIRED_ORDER = 4
REQUIRED_CUT = "strict"
RUNTIME_ASSET_ID = "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_index_v1"
RUNTIME_FORMAT = "grouped_npz_by_length_and_word_shape"


@dataclass(frozen=True)
class RuntimeGroupRef:
    path: str
    direction: str
    ngram_order: int
    dictionary_cut: str
    phrase_token_length: int
    word_token_lengths: tuple[int, ...]
    phrase_count: int
    sha256: str = ""
    chunk_index: int = 0


@dataclass(frozen=True)
class O4Hit:
    sample_id: str
    source_kind: str
    model_name: str
    damage_level: str
    repeat_index: int
    candidate_start: int
    candidate_end: int
    phrase_id: str
    phrase_token_length: int
    word_token_lengths: tuple[int, ...]
    total_phrase_hd: int
    normalised_phrase_hd: float
    sum_count: float
    max_count: float
    sum_log_count: float
    max_log_count: float
    source_row_count: int


@dataclass(frozen=True)
class SampleScanSummary:
    sample_id: str
    source_kind: str
    model_name: str
    damage_level: str
    repeat_index: int
    token_count: int
    changed_fraction: float
    groups_loaded: int
    phrase_rows_considered: int
    windows_considered: int
    verification_attempts: int
    hit_count: int
    exact_hit_count: int
    longest_exact_phrase_len: int
    longest_hit_phrase_len: int
    min_hd_at_len_ge_10: int | None
    min_hd_at_len_ge_12: int | None
    min_hd_at_len_ge_15: int | None
    selected_nonoverlap_exact_count: int
    selected_nonoverlap_exact_weight: float
    elapsed_seconds: float = 0.0


def stable_int_seed(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little", signed=False) & 0x7FFF_FFFF_FFFF_FFFF


def parse_word_lens(value: Any) -> tuple[int, ...]:
    if isinstance(value, str):
        parsed = json.loads(value)
    else:
        parsed = value
    out = tuple(int(item) for item in parsed)
    if len(out) != 4:
        raise ValueError(f"strict O4 group must have four word lengths, got {out!r}")
    return out


def _validate_runtime_manifest_basics(manifest: Mapping[str, Any]) -> None:
    if manifest.get("asset_id") != RUNTIME_ASSET_ID:
        raise ValueError(f"unexpected O4 runtime asset_id={manifest.get('asset_id')!r}")
    if manifest.get("asset_status") not in {"built", "validated", "review_ready", "accepted"}:
        raise ValueError(f"unexpected O4 runtime asset_status={manifest.get('asset_status')!r}")
    if manifest.get("production_scorer_change") is not False:
        raise ValueError("runtime manifest claims production_scorer_change is not false")
    if manifest.get("old_phrase_index_v1_used") is not False:
        raise ValueError("runtime manifest used old phrase_index_v1")
    if manifest.get("sample_asset_used") is not False:
        raise ValueError("runtime manifest used sample asset")
    if list(manifest.get("orders", [])) != [4]:
        raise ValueError(f"runtime manifest orders must be [4], got {manifest.get('orders')!r}")
    if list(manifest.get("directions", [])) != ["fwd"]:
        raise ValueError(f"runtime manifest directions must be ['fwd'], got {manifest.get('directions')!r}")
    if "strict" not in set(manifest.get("cuts", [])):
        raise ValueError("runtime manifest does not contain strict cut")
    if manifest.get("runtime_format") != RUNTIME_FORMAT:
        raise ValueError(f"unexpected runtime_format={manifest.get('runtime_format')!r}")
    if manifest.get("source_compact_validation_status") != "pass":
        raise ValueError("source compact validation did not pass")


def load_strict_o4_runtime_groups(
    manifest_path: Path,
    *,
    min_phrase_token_length: int = 10,
    max_phrase_token_length: int | None = None,
    max_groups: int | None = None,
) -> list[RuntimeGroupRef]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_runtime_manifest_basics(manifest)
    groups: list[RuntimeGroupRef] = []
    for row in manifest.get("files", []):
        if str(row.get("direction")) != REQUIRED_DIRECTION:
            continue
        if int(row.get("ngram_order", -1)) != REQUIRED_ORDER:
            continue
        if str(row.get("dictionary_cut")) != REQUIRED_CUT:
            continue
        phrase_len = int(row.get("phrase_token_length", -1))
        if phrase_len < min_phrase_token_length:
            continue
        if max_phrase_token_length is not None and phrase_len > max_phrase_token_length:
            continue
        groups.append(
            RuntimeGroupRef(
                path=str(row["path"]),
                direction=str(row["direction"]),
                ngram_order=int(row["ngram_order"]),
                dictionary_cut=str(row["dictionary_cut"]),
                phrase_token_length=phrase_len,
                word_token_lengths=parse_word_lens(row["word_token_lengths"]),
                phrase_count=int(row.get("phrase_count", 0)),
                sha256=str(row.get("sha256", "")),
                chunk_index=int(row.get("chunk_index", 0)),
            )
        )
    groups.sort(key=lambda g: (g.phrase_token_length, g.word_token_lengths, g.chunk_index, g.path))
    if max_groups is not None:
        groups = groups[: int(max_groups)]
    if not groups:
        raise ValueError("no strict O4 FWD runtime groups selected")
    return groups


def load_runtime_npz(repo_root: Path, group: RuntimeGroupRef, *, max_phrase_rows: int | None = None) -> Mapping[str, np.ndarray]:
    path = repo_root / group.path
    data = np.load(path, allow_pickle=False)
    required = {
        "rune_tokens",
        "phrase_id",
        "sum_count",
        "max_count",
        "sum_log_count",
        "max_log_count",
        "source_row_count",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise KeyError(f"runtime npz missing fields {missing}: {group.path}")
    out = {name: data[name] for name in data.files}
    row_count = int(out["rune_tokens"].shape[0])
    if max_phrase_rows is not None and row_count > max_phrase_rows:
        row_count = int(max_phrase_rows)
        out = {name: value[:row_count] if getattr(value, "ndim", 0) and value.shape[0] >= row_count else value for name, value in out.items()}
    return out


def hamming_hits_for_group(
    *,
    sample_id: str,
    source_kind: str,
    model_name: str,
    damage_level: str,
    repeat_index: int,
    tokens: Sequence[int],
    group: RuntimeGroupRef,
    payload: Mapping[str, np.ndarray],
    max_total_phrase_hd: int,
) -> tuple[list[O4Hit], int, int, int]:
    arr = np.asarray(tokens, dtype=np.uint16)
    phrase_len = group.phrase_token_length
    if arr.size < phrase_len:
        return [], 0, 0, 0
    phrase_tokens = np.asarray(payload["rune_tokens"], dtype=np.uint16)
    phrase_count = int(phrase_tokens.shape[0])
    hits: list[O4Hit] = []
    windows = int(arr.size) - phrase_len + 1
    attempts = 0
    for start in range(windows):
        window = arr[start : start + phrase_len]
        hd = np.count_nonzero(phrase_tokens != window, axis=1)
        matched = np.flatnonzero(hd <= int(max_total_phrase_hd))
        attempts += phrase_count
        for idx in matched.tolist():
            total_hd = int(hd[idx])
            hits.append(
                O4Hit(
                    sample_id=sample_id,
                    source_kind=source_kind,
                    model_name=model_name,
                    damage_level=damage_level,
                    repeat_index=int(repeat_index),
                    candidate_start=start,
                    candidate_end=start + phrase_len,
                    phrase_id=str(payload["phrase_id"][idx]),
                    phrase_token_length=phrase_len,
                    word_token_lengths=group.word_token_lengths,
                    total_phrase_hd=total_hd,
                    normalised_phrase_hd=total_hd / float(max(1, phrase_len)),
                    sum_count=float(payload["sum_count"][idx]),
                    max_count=float(payload["max_count"][idx]),
                    sum_log_count=float(payload["sum_log_count"][idx]),
                    max_log_count=float(payload["max_log_count"][idx]),
                    source_row_count=int(payload["source_row_count"][idx]),
                )
            )
    return hits, phrase_count, windows, attempts


def exact_anchor_weight(hit: O4Hit, *, total_phrase_rows: float = 447_322_375.0) -> float:
    rarity = math.log1p(max(1.0, total_phrase_rows) / max(1.0, float(hit.source_row_count)))
    length_bonus = 0.20 * max(0, hit.phrase_token_length - 10)
    exact_bonus = 4.0 if hit.total_phrase_hd == 0 else 0.0
    hd_penalty = 0.75 * hit.total_phrase_hd
    return rarity + length_bonus + exact_bonus - hd_penalty


def select_nonoverlap_exact_anchors(hits: Sequence[O4Hit]) -> tuple[int, float]:
    exact_hits = [hit for hit in hits if hit.total_phrase_hd == 0]
    exact_hits.sort(key=lambda hit: (hit.candidate_end, hit.candidate_start, -exact_anchor_weight(hit), hit.phrase_id))
    n = len(exact_hits)
    if n == 0:
        return 0, 0.0
    ends = [hit.candidate_end for hit in exact_hits]
    p: list[int] = []
    for i, hit in enumerate(exact_hits):
        lo, hi = 0, i - 1
        best = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if ends[mid] <= hit.candidate_start:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        p.append(best)
    weights = [exact_anchor_weight(hit) for hit in exact_hits]
    dp = [0.0] * (n + 1)
    take = [False] * n
    for i in range(1, n + 1):
        include = weights[i - 1] + dp[p[i - 1] + 1]
        exclude = dp[i - 1]
        if include > exclude + 1e-12:
            dp[i] = include
            take[i - 1] = True
        else:
            dp[i] = exclude
    count = 0
    i = n
    while i > 0:
        if take[i - 1] and weights[i - 1] + dp[p[i - 1] + 1] >= dp[i - 1] - 1e-12:
            count += 1
            i = p[i - 1] + 1
        else:
            i -= 1
    return count, dp[n]


def min_hd_at_len(hits: Sequence[O4Hit], threshold: int) -> int | None:
    values = [hit.total_phrase_hd for hit in hits if hit.phrase_token_length >= threshold]
    return min(values) if values else None


def summarise_hits(
    *,
    sample_id: str,
    source_kind: str,
    model_name: str,
    damage_level: str,
    repeat_index: int,
    token_count: int,
    changed_fraction: float,
    groups_loaded: int,
    phrase_rows_considered: int,
    windows_considered: int,
    verification_attempts: int,
    hits: Sequence[O4Hit],
    elapsed_seconds: float = 0.0,
) -> SampleScanSummary:
    selected_count, selected_weight = select_nonoverlap_exact_anchors(hits)
    return SampleScanSummary(
        sample_id=sample_id,
        source_kind=source_kind,
        model_name=model_name,
        damage_level=damage_level,
        repeat_index=int(repeat_index),
        token_count=int(token_count),
        changed_fraction=float(changed_fraction),
        groups_loaded=int(groups_loaded),
        phrase_rows_considered=int(phrase_rows_considered),
        windows_considered=int(windows_considered),
        verification_attempts=int(verification_attempts),
        hit_count=len(hits),
        exact_hit_count=sum(1 for hit in hits if hit.total_phrase_hd == 0),
        longest_exact_phrase_len=max((hit.phrase_token_length for hit in hits if hit.total_phrase_hd == 0), default=0),
        longest_hit_phrase_len=max((hit.phrase_token_length for hit in hits), default=0),
        min_hd_at_len_ge_10=min_hd_at_len(hits, 10),
        min_hd_at_len_ge_12=min_hd_at_len(hits, 12),
        min_hd_at_len_ge_15=min_hd_at_len(hits, 15),
        selected_nonoverlap_exact_count=selected_count,
        selected_nonoverlap_exact_weight=selected_weight,
        elapsed_seconds=float(elapsed_seconds),
    )


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count


def append_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    count = 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count


def hit_row(hit: O4Hit) -> dict[str, Any]:
    row = asdict(hit)
    row["word_token_lengths"] = json.dumps(list(hit.word_token_lengths), separators=(",", ":"))
    return row


def summary_row(summary: SampleScanSummary) -> dict[str, Any]:
    return asdict(summary)
