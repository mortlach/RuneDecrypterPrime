from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.scoring.word_ngrams import (
    RuneTokenWordNgramMemoryModel,
    make_prefix_key,
    make_token_ngram_key,
)


TOKENIZED_DIR = REPO_ROOT / "assets_packed/tokenized_pg"
OUTPUT_ROOT = REPO_ROOT / "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets"
RUN_LABEL = "build_word_ngram_sqlite_asset_phase2_v1"
OUTPUT_SQLITE_NAME = "word_ngrams_tokenized64_phase2_v1.sqlite"
BOOK_LIMIT = 64
ORDERS = (3, 4, 5)
PT_KEY = "pt_nose_data"
WLI_KEY = "wli_nose_data"


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _select_word_ngram_books(root: Path, *, limit: int | None) -> list[Path]:
    paths = sorted(root.glob("*_fwd.npz"))
    ranked = sorted(
        paths,
        key=lambda p: (__import__("hashlib").sha1(p.name.encode("utf-8")).hexdigest(), p.name),
    )
    if limit is None or int(limit) <= 0:
        return ranked
    return ranked[: int(limit)]


def _init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
    for n in ORDERS:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS g{int(n)} (
                key BLOB PRIMARY KEY,
                count INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS t{int(n)-1} (
                prefix BLOB PRIMARY KEY,
                total INTEGER NOT NULL
            )
            """
        )
    conn.commit()


def _insert_counts(conn: sqlite3.Connection, model: RuneTokenWordNgramMemoryModel) -> None:
    cur = conn.cursor()
    for n in ORDERS:
        for key, count in sorted(model.counts_by_n.get(int(n), {}).items()):
            cur.execute(
                f"""
                INSERT INTO g{int(n)}(key, count)
                VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET count = excluded.count
                """,
                (sqlite3.Binary(bytes(key)), int(count)),
            )
        prefix_len = int(n) - 1
        for prefix, total in sorted(model.totals_by_prefix_len.get(prefix_len, {}).items()):
            cur.execute(
                f"""
                INSERT INTO t{prefix_len}(prefix, total)
                VALUES(?, ?)
                ON CONFLICT(prefix) DO UPDATE SET total = excluded.total
                """,
                (sqlite3.Binary(bytes(prefix)), int(total)),
            )
    conn.commit()


def main() -> None:
    if not TOKENIZED_DIR.exists():
        raise FileNotFoundError(f"Missing tokenized corpus dir: {TOKENIZED_DIR}")

    books = _select_word_ngram_books(TOKENIZED_DIR, limit=BOOK_LIMIT)
    if not books:
        raise FileNotFoundError(f"No tokenized books found under: {TOKENIZED_DIR}")

    run_dir = OUTPUT_ROOT / f"{_utc_now_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)
    sqlite_fp = run_dir / OUTPUT_SQLITE_NAME

    print("[build_word_ngram_sqlite_asset_phase2_v1] building in-memory counts...", flush=True)
    model = RuneTokenWordNgramMemoryModel.from_tokenized_npz_paths(
        books,
        pt_key=PT_KEY,
        wli_key=WLI_KEY,
        orders=ORDERS,
    )

    print("[build_word_ngram_sqlite_asset_phase2_v1] writing sqlite asset...", flush=True)
    conn = sqlite3.connect(str(sqlite_fp))
    try:
        _init_db(conn)
        _insert_counts(conn, model)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("version", "word_ngrams_tokenized64_phase2_v1"))
        cur.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("book_limit", str(int(BOOK_LIMIT))))
        cur.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("orders_json", json.dumps([int(v) for v in ORDERS])))
        cur.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("pt_key", PT_KEY))
        cur.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("wli_key", WLI_KEY))
        cur.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", ("book_names_json", json.dumps([p.name for p in books])))
        conn.commit()
    finally:
        conn.close()

    run_config = {
        "tokenized_dir": str(TOKENIZED_DIR),
        "book_limit": int(BOOK_LIMIT),
        "orders": [int(v) for v in ORDERS],
        "book_names": [p.name for p in books],
        "sqlite_path": str(sqlite_fp),
    }
    (run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")
    print(f"[build_word_ngram_sqlite_asset_phase2_v1] wrote sqlite: {sqlite_fp}", flush=True)
    print(f"[build_word_ngram_sqlite_asset_phase2_v1] books={len(books)}", flush=True)


if __name__ == "__main__":
    main()
