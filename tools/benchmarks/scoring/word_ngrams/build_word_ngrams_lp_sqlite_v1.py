from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, Tuple


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


# Edit constants here. No CLI.
NGRAM_SOURCE_ROOT = Path(r"C:\path\to\google_ngrams_Version-20200217")
NGRAM_DIRS = {3: "3-grams", 4: "4-grams", 5: "5-grams"}
OUTPUT_SQLITE = Path(r"C:\path\to\assets\word_ngrams_lp_v1.sqlite")
COMMIT_EVERY_ROWS = 200_000
JOURNAL_MODE = "WAL"
SYNCHRONOUS = "NORMAL"
CACHE_PAGES = 200_000
VALIDATE_FILENAME_COUNTS = True
WORD_SEP_BYTE = 0xFF
KEY_SEP = bytes([WORD_SEP_BYTE])


@dataclass(frozen=True)
class ParsedLine:
    words: Tuple[str, ...]
    count: int


def parse_line(line: str, n: int) -> ParsedLine | None:
    text = line.strip()
    if not text:
        return None
    parts = text.split()
    if len(parts) != n + 1:
        return None
    *words, count_s = parts
    try:
        count = int(count_s)
    except ValueError:
        return None
    return ParsedLine(words=tuple(w.lower() for w in words), count=count)


_ENCODE_CACHE: Dict[str, bytes] = {}


def encode_word_to_token(word: str) -> bytes:
    cached = _ENCODE_CACHE.get(word)
    if cached is not None:
        return cached
    idx, _wli, _runes = Runeglish.encode_english_to_runes(word, direction="ltr")
    if not idx:
        token = b""
    else:
        if WORD_SEP_BYTE in idx:
            raise ValueError("Separator byte appears in rune indices; choose another separator.")
        token = bytes(int(v) for v in idx)
    _ENCODE_CACHE[word] = token
    return token


def iter_txt_files(dir_path: Path) -> Iterator[Path]:
    for fp in dir_path.rglob("*.txt"):
        if fp.is_file():
            yield fp


def parse_filename_counts(fp: Path, n: int) -> Tuple[int, ...] | None:
    parts = fp.stem.strip().split()
    if len(parts) != n:
        return None
    try:
        return tuple(int(x) for x in parts)
    except ValueError:
        return None


def make_key(tokens: Tuple[bytes, ...]) -> bytes:
    return KEY_SEP.join(tokens)


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(f"PRAGMA journal_mode={JOURNAL_MODE};")
    cur.execute(f"PRAGMA synchronous={SYNCHRONOUS};")
    cur.execute(f"PRAGMA cache_size={-int(CACHE_PAGES)};")
    cur.execute("PRAGMA temp_store=MEMORY;")
    cur.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
    for n in (3, 4, 5):
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS g{n} (
                key BLOB PRIMARY KEY,
                count INTEGER NOT NULL
            );
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS t{n-1} (
                prefix BLOB PRIMARY KEY,
                total INTEGER NOT NULL
            );
            """
        )
    conn.commit()


def upsert_add(cur: sqlite3.Cursor, table: str, key_col: str, key: bytes, val_col: str, val: int) -> None:
    cur.execute(
        f"""
        INSERT INTO {table}({key_col}, {val_col})
        VALUES (?, ?)
        ON CONFLICT({key_col}) DO UPDATE SET {val_col} = {val_col} + excluded.{val_col}
        """,
        (sqlite3.Binary(key), int(val)),
    )


def build_n(conn: sqlite3.Connection, n: int, dir_path: Path) -> None:
    cur = conn.cursor()
    gram_table = f"g{n}"
    tot_table = f"t{n-1}"
    rows = 0
    for fp in iter_txt_files(dir_path):
        expected_counts = parse_filename_counts(fp, n) if VALIDATE_FILENAME_COUNTS else None
        with fp.open("r", encoding="utf-8") as handle:
            for line in handle:
                parsed = parse_line(line, n=n)
                if parsed is None:
                    continue
                tokens = tuple(encode_word_to_token(w) for w in parsed.words)
                if any(t == b"" for t in tokens):
                    continue
                if expected_counts is not None:
                    got = tuple(len(t) for t in tokens)
                    if got != expected_counts:
                        raise ValueError(
                            f"Filename counts mismatch in {fp.name}: expected={expected_counts} got={got}"
                        )
                upsert_add(cur, gram_table, "key", make_key(tokens), "count", parsed.count)
                upsert_add(cur, tot_table, "prefix", make_key(tokens[:-1]), "total", parsed.count)
                rows += 1
                if rows % COMMIT_EVERY_ROWS == 0:
                    conn.commit()
                    print(f"[build] n={n} rows={rows:,} file={fp.name}", flush=True)
    conn.commit()
    print(f"[build] n={n} DONE rows={rows:,}", flush=True)


def main() -> None:
    if not NGRAM_SOURCE_ROOT.exists():
        raise FileNotFoundError(f"NGRAM_SOURCE_ROOT not found: {NGRAM_SOURCE_ROOT}")
    OUTPUT_SQLITE.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_SQLITE.exists():
        raise FileExistsError(f"Refusing to overwrite existing DB: {OUTPUT_SQLITE}")

    conn = sqlite3.connect(str(OUTPUT_SQLITE))
    try:
        init_db(conn)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("version", "word_ngrams_lp_v1"))
        cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("sep_byte", str(WORD_SEP_BYTE)))
        conn.commit()
        for n, subdir in NGRAM_DIRS.items():
            src = NGRAM_SOURCE_ROOT / subdir
            if not src.exists():
                raise FileNotFoundError(f"Missing {n}-gram dir: {src}")
            build_n(conn, n=n, dir_path=src)
        print(f"[build] wrote sqlite: {OUTPUT_SQLITE}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
