from __future__ import annotations

"""
Build balanced explicit book lists for PhaseB Runeberg medium summary runs.

IDE-friendly: edit constants and run this file. No CLI arguments.
"""

import csv
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


TOKENIZED_ROOT_REL = "../language_model_prime/lmprime_out/tokenized"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/book_lists"
PC_A_LIST_REL = OUTPUT_DIR_REL + "/medium_pc_a.txt"
PC_B_LIST_REL = OUTPUT_DIR_REL + "/medium_pc_b.txt"
SUMMARY_CSV_REL = OUTPUT_DIR_REL + "/medium_book_list_summary.csv"
DIRECTIONS = ("fwd", "rev")
EXCLUDE_BOOKS = (
    "1-0.txt",
    "10004.txt",
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    cwd = Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root; expected parent containing src/ and tools/")


REPO_ROOT = _find_repo_root()


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), REPO_ROOT.resolve()).replace(os.sep, "/")


def _resolve_from_repo_root(path_text: str) -> Path:
    return (REPO_ROOT / path_text).resolve()


def _book_name_from_tokenized(path: Path, direction: str) -> str:
    suffix = f"_{direction}.npz"
    name = path.name
    if not name.endswith(suffix):
        raise ValueError(f"tokenized file does not end with {suffix!r}: {path.name}")
    return name[: -len(suffix)]


def discover_tokenized_files(tokenized_root: Path) -> list[tuple[str, str, Path]]:
    rows: list[tuple[str, str, Path]] = []
    for direction in DIRECTIONS:
        for path in sorted(tokenized_root.glob(f"*_{direction}.npz")):
            rows.append((_book_name_from_tokenized(path, direction), direction, path))
    rows.sort(key=lambda row: (row[0], row[1]))
    return rows


def complete_book_size_rows(rows: Sequence[tuple[str, str, Path]]) -> list[dict[str, Any]]:
    by_book: dict[str, dict[str, Path]] = {}
    for book, direction, path in rows:
        by_book.setdefault(book, {})[direction] = path

    out: list[dict[str, Any]] = []
    excluded = set(EXCLUDE_BOOKS)
    for book in sorted(by_book):
        if book in excluded:
            continue
        paths = by_book[book]
        if not all(direction in paths for direction in DIRECTIONS):
            continue
        fwd_size = paths["fwd"].stat().st_size
        rev_size = paths["rev"].stat().st_size
        out.append(
            {
                "book": book,
                "fwd_path": _repo_rel(paths["fwd"]),
                "rev_path": _repo_rel(paths["rev"]),
                "fwd_bytes": fwd_size,
                "rev_bytes": rev_size,
                "pair_bytes": fwd_size + rev_size,
            }
        )
    return out


def greedy_two_way_balance(book_rows: Sequence[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    left: list[Mapping[str, Any]] = []
    right: list[Mapping[str, Any]] = []
    left_bytes = 0
    right_bytes = 0
    for row in sorted(book_rows, key=lambda item: (-int(item["pair_bytes"]), str(item["book"]))):
        if left_bytes <= right_bytes:
            left.append(row)
            left_bytes += int(row["pair_bytes"])
        else:
            right.append(row)
            right_bytes += int(row["pair_bytes"])
    return sorted(left, key=lambda item: str(item["book"])), sorted(right, key=lambda item: str(item["book"]))


def _write_book_list(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(str(row["book"]) for row in rows) + ("\n" if rows else "")
    path.write_text(text, encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _assignment_rows(label: str, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "assignment": label,
                "book": row["book"],
                "fwd_bytes": row["fwd_bytes"],
                "rev_bytes": row["rev_bytes"],
                "pair_bytes": row["pair_bytes"],
                "fwd_path": row["fwd_path"],
                "rev_path": row["rev_path"],
            }
        )
    return out


def validate_no_overlap(left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]) -> None:
    left_books = {str(row["book"]) for row in left}
    right_books = {str(row["book"]) for row in right}
    overlap = sorted(left_books & right_books)
    if overlap:
        raise AssertionError(f"balanced book lists overlap: {overlap}")


def run_once() -> dict[str, Any]:
    tokenized_root = _resolve_from_repo_root(TOKENIZED_ROOT_REL)
    if not tokenized_root.exists():
        raise FileNotFoundError(f"TOKENIZED_ROOT not found: {_repo_rel(tokenized_root)}")

    rows = discover_tokenized_files(tokenized_root)
    book_rows = complete_book_size_rows(rows)
    left, right = greedy_two_way_balance(book_rows)
    validate_no_overlap(left, right)

    pc_a_path = _resolve_from_repo_root(PC_A_LIST_REL)
    pc_b_path = _resolve_from_repo_root(PC_B_LIST_REL)
    summary_path = _resolve_from_repo_root(SUMMARY_CSV_REL)

    _write_book_list(pc_a_path, left)
    _write_book_list(pc_b_path, right)
    summary_rows = _assignment_rows("pc_a", left) + _assignment_rows("pc_b", right)
    _write_csv(
        summary_path,
        summary_rows,
        ("assignment", "book", "fwd_bytes", "rev_bytes", "pair_bytes", "fwd_path", "rev_path"),
    )

    left_bytes = sum(int(row["pair_bytes"]) for row in left)
    right_bytes = sum(int(row["pair_bytes"]) for row in right)
    summary = {
        "complete_books": len(book_rows),
        "pc_a_books": len(left),
        "pc_b_books": len(right),
        "pc_a_pair_bytes": left_bytes,
        "pc_b_pair_bytes": right_bytes,
        "byte_imbalance": abs(left_bytes - right_bytes),
        "pc_a_list": _repo_rel(pc_a_path),
        "pc_b_list": _repo_rel(pc_b_path),
        "summary_csv": _repo_rel(summary_path),
    }
    print(
        "[phaseB_book_lists] "
        f"complete_books={summary['complete_books']} pc_a_books={summary['pc_a_books']} "
        f"pc_b_books={summary['pc_b_books']} byte_imbalance={summary['byte_imbalance']} "
        f"pc_a={summary['pc_a_list']} pc_b={summary['pc_b_list']}",
        flush=True,
    )
    return summary


if __name__ == "__main__":
    run_once()
