from __future__ import annotations
import csv
from pathlib import Path
from rune_decrypter_prime.data.asset_paths import resolve_assets_path
from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists
from rune_decrypter_prime.utils.runeglish import Runeglish

PHASEA14_REL_ROOT = "hamming_dictionary_policies_phaseA_v0_14"
EXPECTED_RAW_FILES = {f"raw1grams_{idx:02d}.csv" for idx in range(1, 15)} | {
    "raw1grams_a1.csv"
}
EXPECTED_SELECTED_COUNTS = {"strict": 9541, "normal": 30695}
EXPECTED_A1_SELECTED_COUNTS = {"strict": 0, "normal": 12}


def _policy_dir(policy: str) -> Path:
    return resolve_assets_path(
        PHASEA14_REL_ROOT, policy, "hamming_raw_1g", start=Path(__file__)
    )


def _selected_rows(policy: str) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for fp in sorted(_policy_dir(policy).glob("raw1grams_*.csv")):
        with fp.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.reader(fh):
                assert len(row) >= 5, f"{fp.name} has a short row: {row!r}"
                assert row[2] in {
                    "0",
                    "1",
                }, f"{fp.name} has a non-binary selected flag: {row[2]!r}"
                if row[2] == "1":
                    rows.append((row[0], row[1], row[2], row[3], row[4]))
    return rows


def _selected_count_for_file(policy: str, file_name: str) -> int:
    fp = _policy_dir(policy) / file_name
    count = 0
    with fp.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) >= 3 and row[2] == "1":
                count += 1
    return count


def test_phaseA_v0_14_raw1grams_asset_files_exist() -> None:
    for policy in ("strict", "normal"):
        policy_dir = _policy_dir(policy)
        assert policy_dir.exists(), policy_dir
        observed = {fp.name for fp in policy_dir.glob("raw1grams_*.csv")}
        assert observed == EXPECTED_RAW_FILES


def test_phaseA_v0_14_selected_counts_are_locked() -> None:
    for policy, expected_count in EXPECTED_SELECTED_COUNTS.items():
        assert len(_selected_rows(policy)) == expected_count
        assert (
            _selected_count_for_file(policy, "raw1grams_a1.csv")
            == EXPECTED_A1_SELECTED_COUNTS[policy]
        )


def test_phaseA_v0_14_strict_selected_is_subset_of_normal_selected() -> None:
    strict = {
        (word, runes, row_hash)
        for word, _count, _selected, runes, row_hash in _selected_rows("strict")
    }
    normal = {
        (word, runes, row_hash)
        for word, _count, _selected, runes, row_hash in _selected_rows("normal")
    }
    assert strict <= normal


def test_phaseA_v0_14_selected_rune_lengths_match_file_names() -> None:
    for policy in ("strict", "normal"):
        for fp in sorted(_policy_dir(policy).glob("raw1grams_*.csv")):
            expected_len = (
                4 if fp.name == "raw1grams_a1.csv" else int(fp.stem.rsplit("_", 1)[1])
            )
            with fp.open("r", encoding="utf-8", newline="") as fh:
                for row in csv.reader(fh):
                    if len(row) < 5 or row[2] != "1":
                        continue
                    rune_indices = Runeglish.rune_to_pos(row[3])
                    assert len(rune_indices) == expected_len, (
                        policy,
                        fp.name,
                        row[0],
                        row[3],
                    )


def test_phaseA_v0_14_loader_reads_selected_wordlists() -> None:
    strict_wordlists, _ = load_raw1grams_wordlists(
        _policy_dir("strict"), require_selected=True
    )
    normal_wordlists, _ = load_raw1grams_wordlists(
        _policy_dir("normal"), require_selected=True
    )
    assert (
        sum((len(rows) for rows in strict_wordlists.values()))
        == EXPECTED_SELECTED_COUNTS["strict"]
    )
    assert (
        sum((len(rows) for rows in normal_wordlists.values()))
        == EXPECTED_SELECTED_COUNTS["normal"]
    )
    assert 14 in strict_wordlists
    assert 14 in normal_wordlists
