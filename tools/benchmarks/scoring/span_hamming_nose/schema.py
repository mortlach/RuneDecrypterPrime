from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


SUITE_VERSION = "span_hamming_nose_v2"
NPZ_TOKEN_KEY = "pt_nose_data"
DEFAULT_LENGTH_BUCKETS = (20, 50, 100, 200, 300, 500, 600, 750, 1000, 1500, 2400)
DEFAULT_GENERATORS = (
    "REAL",
    "RAND_UNIGRAM",
    "SHUFFLE_UNIGRAM",
    "CORRUPT_10",
    "CORRUPT_20",
    "CORRUPT_50",
)


@dataclass(frozen=True)
class CorpusRecord:
    book_id: str
    path: Path
    direction: str
    token_key: str
    tokens: np.ndarray


@dataclass(frozen=True)
class PlanRow:
    row_idx: int
    row_id: str
    direction: str
    length_bucket: int
    book_id: str
    book_path: str
    start: int
    text_length: int
    stride: int

    @staticmethod
    def csv_header() -> list[str]:
        return [
            "row_idx",
            "row_id",
            "direction",
            "length_bucket",
            "book_id",
            "book_path",
            "start",
            "text_length",
            "stride",
        ]

    def as_csv_row(self) -> dict[str, str]:
        return {
            "row_idx": str(self.row_idx),
            "row_id": self.row_id,
            "direction": self.direction,
            "length_bucket": str(self.length_bucket),
            "book_id": self.book_id,
            "book_path": self.book_path,
            "start": str(self.start),
            "text_length": str(self.text_length),
            "stride": str(self.stride),
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "PlanRow":
        return cls(
            row_idx=int(row["row_idx"]),
            row_id=str(row["row_id"]),
            direction=str(row["direction"]),
            length_bucket=int(row["length_bucket"]),
            book_id=str(row["book_id"]),
            book_path=str(row["book_path"]),
            start=int(row["start"]),
            text_length=int(row["text_length"]),
            stride=int(row["stride"]),
        )


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def hash_object(payload: Any) -> str:
    return sha256_hex(canonical_json_bytes(payload))


def deterministic_seed(
    *,
    global_seed: int,
    direction: str,
    length_bucket: int,
    span_cfg_hash: str,
) -> int:
    token = f"{int(global_seed)}|{direction}|{int(length_bucket)}|{span_cfg_hash}"
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="little", signed=False) & 0x7FFFFFFF


def stable_int(*parts: Any) -> int:
    token = "|".join(str(x) for x in parts)
    digest = hashlib.sha1(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="little", signed=False)


def row_id_for_plan(
    *,
    direction: str,
    length_bucket: int,
    book_id: str,
    start: int,
    text_length: int,
    stride: int,
    global_seed: int,
) -> str:
    token = (
        f"{direction}|{int(length_bucket)}|{book_id}|{int(start)}|{int(text_length)}|"
        f"{int(stride)}|{int(global_seed)}"
    )
    return sha256_hex(token.encode("utf-8"))


def _direction_from_filename(path: Path) -> str | None:
    name = path.name.lower()
    if name.endswith("_fwd.npz"):
        return "ltr"
    if name.endswith("_rev.npz"):
        return "rtl"
    return None


def discover_npz_paths(
    *,
    tokenized_dir: str | Path,
    directions: Sequence[str],
) -> list[Path]:
    root = Path(tokenized_dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"tokenized_dir not found: {root}")
    wanted = {str(x).strip().lower() for x in directions}
    if not wanted.issubset({"ltr", "rtl"}):
        raise ValueError("directions must be a subset of {'ltr','rtl'}")

    paths: list[Path] = []
    if "ltr" in wanted:
        paths.extend(sorted(root.glob("*_fwd.npz")))
    if "rtl" in wanted:
        paths.extend(sorted(root.glob("*_rev.npz")))
    unique = sorted({p.resolve() for p in paths if p.is_file()})
    if not unique:
        raise FileNotFoundError(
            f"No tokenized npz files found under {root} for directions={sorted(wanted)}"
        )
    return unique


def load_tokens_from_npz(
    npz_path: Path,
    *,
    min_length: int = 1,
) -> tuple[np.ndarray, str]:
    with np.load(npz_path, allow_pickle=False) as data:
        if NPZ_TOKEN_KEY not in data:
            raise ValueError(f"{npz_path}: missing required key '{NPZ_TOKEN_KEY}'")
        raw = np.asarray(data[NPZ_TOKEN_KEY])
    if raw.ndim != 1:
        raise ValueError(f"{npz_path}: token array must be rank-1")
    if raw.size < int(min_length):
        raise ValueError(f"{npz_path}: token array shorter than min_length={min_length}")
    if not np.issubdtype(raw.dtype, np.integer):
        raise ValueError(f"{npz_path}: token array must be integer dtype")
    tokens = raw.astype(np.int64, copy=False)
    if np.any(tokens < 0) or np.any(tokens > 28):
        raise ValueError(f"{npz_path}: token values must be in [0, 28]")
    return tokens.astype(np.uint8, copy=False), NPZ_TOKEN_KEY


def load_corpus_records(
    npz_paths: Sequence[Path],
    *,
    min_length: int = 1,
    directions: Sequence[str] = ("ltr", "rtl"),
) -> list[CorpusRecord]:
    wanted = {str(x).strip().lower() for x in directions}
    records: list[CorpusRecord] = []
    for path in sorted(npz_paths):
        direction = _direction_from_filename(path)
        if direction is None or direction not in wanted:
            continue
        tokens, key = load_tokens_from_npz(path, min_length=min_length)
        records.append(
            CorpusRecord(
                book_id=path.stem,
                path=path,
                direction=direction,
                token_key=key,
                tokens=tokens,
            )
        )
    return records


def corpus_list_hash(records: Sequence[CorpusRecord]) -> str:
    payload = [
        {
            "book_id": rec.book_id,
            "path": str(rec.path),
            "direction": rec.direction,
            "token_key": rec.token_key,
            "n_tokens": int(rec.tokens.size),
        }
        for rec in records
    ]
    return hash_object(payload)


def estimate_unigram_probs_by_direction(records: Sequence[CorpusRecord]) -> dict[str, np.ndarray]:
    counts: dict[str, np.ndarray] = {
        "ltr": np.zeros((29,), dtype=np.float64),
        "rtl": np.zeros((29,), dtype=np.float64),
    }
    for rec in records:
        vals, freq = np.unique(rec.tokens.astype(np.int64, copy=False), return_counts=True)
        counts[rec.direction][vals] += freq
    probs: dict[str, np.ndarray] = {}
    for direction, dir_counts in counts.items():
        total = float(np.sum(dir_counts))
        if total <= 0.0:
            probs[direction] = np.full((29,), 1.0 / 29.0, dtype=np.float64)
        else:
            probs[direction] = dir_counts / total
    return probs


def _deterministic_offset(
    *,
    book_id: str,
    direction: str,
    length_bucket: int,
    global_seed: int,
    stride: int,
) -> int:
    if stride <= 0:
        return 0
    return int(stable_int(book_id, direction, int(length_bucket), int(global_seed)) % int(stride))


def plan_starts_for_book(
    *,
    book_id: str,
    direction: str,
    n_tokens: int,
    length_bucket: int,
    stride: int,
    global_seed: int,
    max_windows: int,
) -> list[int]:
    if n_tokens < int(length_bucket):
        return []
    offset = _deterministic_offset(
        book_id=book_id,
        direction=direction,
        length_bucket=length_bucket,
        global_seed=global_seed,
        stride=stride,
    )
    limit = n_tokens - int(length_bucket)
    starts = list(range(offset, limit + 1, int(stride)))
    if int(max_windows) > 0 and len(starts) > int(max_windows):
        starts = starts[: int(max_windows)]
    return starts


def build_stride_plan(
    *,
    records: Sequence[CorpusRecord],
    directions: Sequence[str],
    length_buckets: Sequence[int],
    global_seed: int,
    min_stride: int,
    stride_factor: float,
    max_windows_per_book_by_l: dict[int, int],
    fallback_max_windows: int,
) -> list[PlanRow]:
    if min_stride < 1:
        raise ValueError("min_stride must be >= 1")
    if stride_factor <= 0.0:
        raise ValueError("stride_factor must be > 0")

    wanted = [str(x).strip().lower() for x in directions]
    by_direction: dict[str, list[CorpusRecord]] = {d: [] for d in wanted}
    for rec in records:
        if rec.direction in by_direction:
            by_direction[rec.direction].append(rec)
    for direction in by_direction:
        by_direction[direction] = sorted(by_direction[direction], key=lambda r: r.book_id)

    rows: list[PlanRow] = []
    for direction in wanted:
        recs = by_direction.get(direction, [])
        for length_bucket in sorted(int(x) for x in length_buckets):
            stride = max(int(min_stride), int(stride_factor * int(length_bucket)))
            max_windows = int(max_windows_per_book_by_l.get(length_bucket, fallback_max_windows))
            for rec in recs:
                starts = plan_starts_for_book(
                    book_id=rec.book_id,
                    direction=direction,
                    n_tokens=int(rec.tokens.size),
                    length_bucket=length_bucket,
                    stride=stride,
                    global_seed=global_seed,
                    max_windows=max_windows,
                )
                for start in starts:
                    row_id = row_id_for_plan(
                        direction=direction,
                        length_bucket=length_bucket,
                        book_id=rec.book_id,
                        start=start,
                        text_length=length_bucket,
                        stride=stride,
                        global_seed=global_seed,
                    )
                    rows.append(
                        PlanRow(
                            row_idx=0,
                            row_id=row_id,
                            direction=direction,
                            length_bucket=length_bucket,
                            book_id=rec.book_id,
                            book_path=str(rec.path),
                            start=int(start),
                            text_length=int(length_bucket),
                            stride=int(stride),
                        )
                    )

    rows.sort(key=lambda r: (r.direction, r.length_bucket, r.book_id, r.start))
    out: list[PlanRow] = []
    for idx, row in enumerate(rows):
        out.append(
            PlanRow(
                row_idx=idx,
                row_id=row.row_id,
                direction=row.direction,
                length_bucket=row.length_bucket,
                book_id=row.book_id,
                book_path=row.book_path,
                start=row.start,
                text_length=row.text_length,
                stride=row.stride,
            )
        )
    return out


def read_plan_csv(path: Path) -> list[PlanRow]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [PlanRow.from_csv_row(row) for row in reader]


def write_plan_csv(path: Path, rows: Sequence[PlanRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PlanRow.csv_header())
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv_row())


def percentile_iqr(values: Sequence[float]) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    q25 = float(np.quantile(arr, 0.25))
    q75 = float(np.quantile(arr, 0.75))
    return q75 - q25


def normalize_span_score(span_raw: float, rand_ref: float, real_ref: float, eps: float = 1e-12) -> float:
    denom = float(real_ref - rand_ref)
    if denom <= float(eps):
        return 0.0
    value = (float(span_raw) - float(rand_ref)) / denom
    return float(np.clip(value, 0.0, 1.0))
