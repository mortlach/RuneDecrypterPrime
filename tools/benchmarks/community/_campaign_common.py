from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

from tools.benchmarks.periodic_sub_trans.common.core_enums import BenchmarkOrder

VALID_ORDERS: tuple[str, str] = (
    BenchmarkOrder.COL_THEN_SUB.value,
    BenchmarkOrder.SUB_THEN_COL.value,
)

INTEGRITY_CHAIN_VERSION = "v1"
INTEGRITY_CHAIN_HASH = "sha256"
INTEGRITY_CHAIN_GENESIS = "RDP_COMMUNITY_RESULTS_CHAIN_V1"


def _normalise_floats(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite float is not allowed in canonical JSON: {value!r}")
        # Fixed v1.1 rule: 12 significant digits before hashing.
        return float(f"{value:.12g}")
    if isinstance(value, dict):
        return {str(k): _normalise_floats(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise_floats(v) for v in value]
    return value


def canonical_json_bytes(payload: Any) -> bytes:
    normalised = _normalise_floats(payload)
    text = json.dumps(
        normalised,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return text.encode("utf-8")


def sha256_hex_from_obj(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def stable_int_from_obj(payload: Any, *, bits: int = 63) -> int:
    if bits <= 0 or bits > 256:
        raise ValueError(f"bits must be in [1, 256], got {bits}")
    digest = hashlib.sha256(canonical_json_bytes(payload)).digest()
    full = int.from_bytes(digest, byteorder="big", signed=False)
    return full & ((1 << bits) - 1)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError(f"JSONL row must be object: {path}:{line_no}")
        rows.append(parsed)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False))
            f.write("\n")


def resolve_orders(raw_orders: Sequence[str]) -> tuple[str, ...]:
    requested = list(raw_orders)
    invalid = [value for value in requested if value not in VALID_ORDERS]
    if invalid:
        raise ValueError(f"unsupported order(s): {invalid}; allowed={list(VALID_ORDERS)}")
    # Canonical order independent of input list ordering.
    return tuple(order for order in VALID_ORDERS if order in requested)


def build_result_integrity_row(
    *,
    result_row: dict[str, Any],
    row_index: int,
    prev_chain_hash: str,
) -> dict[str, Any]:
    idx = int(row_index)
    if idx < 0:
        raise ValueError(f"row_index must be >= 0, got {idx}")
    prev = str(prev_chain_hash).strip()
    if not prev:
        raise ValueError("prev_chain_hash must be non-empty")

    row_hash = sha256_hex_from_obj(result_row)
    chain_hash = sha256_hex_from_obj(
        {
            "integrity_version": INTEGRITY_CHAIN_VERSION,
            "row_index": idx,
            "prev_chain_hash": prev,
            "row_hash": row_hash,
        }
    )
    return {
        "integrity_version": INTEGRITY_CHAIN_VERSION,
        "row_index": idx,
        "job_id": str(result_row.get("job_id", "")),
        "row_hash": row_hash,
        "prev_chain_hash": prev,
        "chain_hash": chain_hash,
    }


def build_results_integrity_rows(
    result_rows: Sequence[dict[str, Any]],
    *,
    start_row_index: int = 0,
    start_prev_chain_hash: str = INTEGRITY_CHAIN_GENESIS,
) -> tuple[list[dict[str, Any]], str]:
    idx = int(start_row_index)
    if idx < 0:
        raise ValueError(f"start_row_index must be >= 0, got {idx}")
    prev = str(start_prev_chain_hash).strip()
    if not prev:
        raise ValueError("start_prev_chain_hash must be non-empty")

    out: list[dict[str, Any]] = []
    for row in result_rows:
        entry = build_result_integrity_row(
            result_row=row,
            row_index=idx,
            prev_chain_hash=prev,
        )
        out.append(entry)
        idx += 1
        prev = str(entry["chain_hash"])
    return out, prev


def verify_results_integrity(
    *,
    result_rows: Sequence[dict[str, Any]],
    integrity_rows: Sequence[dict[str, Any]],
    start_row_index: int = 0,
    start_prev_chain_hash: str = INTEGRITY_CHAIN_GENESIS,
) -> tuple[list[str], str]:
    errors: list[str] = []
    idx = int(start_row_index)
    if idx < 0:
        return ([f"start_row_index must be >= 0, got {idx}"], str(start_prev_chain_hash))
    prev = str(start_prev_chain_hash).strip()
    if not prev:
        return (["start_prev_chain_hash must be non-empty"], str(start_prev_chain_hash))

    if len(result_rows) != len(integrity_rows):
        errors.append(
            "integrity row count mismatch: "
            f"results={len(result_rows)} integrity={len(integrity_rows)}"
        )
        return errors, prev

    for offset, (row, entry) in enumerate(zip(result_rows, integrity_rows)):
        if not isinstance(entry, dict):
            errors.append(f"integrity row {offset} is not an object")
            break

        expected = build_result_integrity_row(
            result_row=row,
            row_index=idx,
            prev_chain_hash=prev,
        )

        for key in ("integrity_version", "row_index", "job_id", "row_hash", "prev_chain_hash", "chain_hash"):
            if entry.get(key) != expected.get(key):
                errors.append(
                    f"integrity row {offset} mismatch for {key}: "
                    f"expected={expected.get(key)!r} got={entry.get(key)!r}"
                )
                break
        if errors:
            break

        idx += 1
        prev = str(expected["chain_hash"])

    return errors, prev
