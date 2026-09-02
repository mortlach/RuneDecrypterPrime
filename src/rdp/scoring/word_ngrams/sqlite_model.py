from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


WORD_SEP_BYTE = 0xFF
KEY_SEP = bytes([WORD_SEP_BYTE])


def make_token_ngram_key(tokens: tuple[bytes, ...] | list[bytes]) -> bytes:
    return KEY_SEP.join(bytes(token) for token in tokens)


def make_prefix_key(tokens: tuple[bytes, ...] | list[bytes]) -> bytes:
    return KEY_SEP.join(bytes(token) for token in tokens)


@dataclass(frozen=True)
class RuneTokenWordNgramSqlite:
    path: Path
    conn: sqlite3.Connection

    @classmethod
    def open(cls, path: str | Path) -> "RuneTokenWordNgramSqlite":
        fp = Path(path).expanduser().resolve()
        if not fp.exists():
            raise FileNotFoundError(f"Rune-token ngram sqlite not found: {fp}")
        conn = sqlite3.connect(str(fp))
        conn.row_factory = sqlite3.Row
        return cls(path=fp, conn=conn)

    def close(self) -> None:
        self.conn.close()

    def meta(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (str(key),)).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def get_ngram_count(self, n: int, key: bytes) -> int:
        row = self.conn.execute(
            f"SELECT count FROM g{int(n)} WHERE key = ?",
            (sqlite3.Binary(bytes(key)),),
        ).fetchone()
        return 0 if row is None else int(row["count"])

    def get_prefix_total(self, n_minus_1: int, prefix: bytes) -> int:
        row = self.conn.execute(
            f"SELECT total FROM t{int(n_minus_1)} WHERE prefix = ?",
            (sqlite3.Binary(bytes(prefix)),),
        ).fetchone()
        return 0 if row is None else int(row["total"])

    def __enter__(self) -> "RuneTokenWordNgramSqlite":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()


__all__ = [
    "KEY_SEP",
    "WORD_SEP_BYTE",
    "RuneTokenWordNgramSqlite",
    "make_prefix_key",
    "make_token_ngram_key",
]
