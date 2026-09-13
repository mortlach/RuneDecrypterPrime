from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest
from rdp.scoring.word_ngrams import RuneTokenWordNgramMemoryModel, RuneTokenWordNgramScorer, RuneTokenWordNgramSqlite, make_prefix_key, make_token_ngram_key
pytestmark = pytest.mark.tier_a

def _init_sqlite(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        for n in (3, 4, 5):
            cur.execute(f'CREATE TABLE g{n} (key BLOB PRIMARY KEY, count INTEGER NOT NULL)')
            cur.execute(f'CREATE TABLE t{n - 1} (prefix BLOB PRIMARY KEY, total INTEGER NOT NULL)')
        conn.commit()
    finally:
        conn.close()

def _write_model_to_sqlite(path: Path, model: RuneTokenWordNgramMemoryModel) -> None:
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        for n, counts in model.counts_by_n.items():
            for key, count in counts.items():
                cur.execute(f'INSERT INTO g{int(n)}(key, count) VALUES(?, ?)', (sqlite3.Binary(bytes(key)), int(count)))
        for prefix_len, totals in model.totals_by_prefix_len.items():
            for prefix, total in totals.items():
                cur.execute(f'INSERT INTO t{int(prefix_len)}(prefix, total) VALUES(?, ?)', (sqlite3.Binary(bytes(prefix)), int(total)))
        conn.commit()
    finally:
        conn.close()

def test_sqlite_model_matches_in_memory_counts_and_scores(tmp_path: Path) -> None:
    sequences = [(b'a', b'b', b'c', b'd', b'e'), (b'a', b'b', b'c', b'd', b'f'), (b'x', b'b', b'c', b'd', b'g')]
    model = RuneTokenWordNgramMemoryModel.from_token_sequences(sequences, orders=(3, 4, 5))
    sqlite_fp = tmp_path / 'toy.sqlite'
    _init_sqlite(sqlite_fp)
    _write_model_to_sqlite(sqlite_fp, model)
    with RuneTokenWordNgramSqlite.open(sqlite_fp) as sqlite_model:
        assert sqlite_model.get_ngram_count(3, make_token_ngram_key((b'a', b'b', b'c'))) == 2
        assert sqlite_model.get_prefix_total(2, make_prefix_key((b'a', b'b'))) == 2
        mem_scorer = RuneTokenWordNgramScorer(model, alpha=0.4, miss_logp=-20.0)
        sql_scorer = RuneTokenWordNgramScorer(sqlite_model, alpha=0.4, miss_logp=-20.0)
        mem_diag = mem_scorer.score_segments_with_diagnostics([(b'a', b'b', b'c', b'd', b'e')])
        sql_diag = sql_scorer.score_segments_with_diagnostics([(b'a', b'b', b'c', b'd', b'e')])
        assert sql_diag.score.n_positions == mem_diag.score.n_positions
        assert sql_diag.score.xent_3 == pytest.approx(mem_diag.score.xent_3, abs=1e-12)
        assert sql_diag.score.xent_backoff_5_4_3 == pytest.approx(mem_diag.score.xent_backoff_5_4_3, abs=1e-12)
        assert sql_diag.score.used5_rate == pytest.approx(mem_diag.score.used5_rate, abs=1e-12)
        assert sql_diag.score.used4_rate == pytest.approx(mem_diag.score.used4_rate, abs=1e-12)
        assert sql_diag.score.used3_rate == pytest.approx(mem_diag.score.used3_rate, abs=1e-12)
        assert sql_diag.score.miss_rate == pytest.approx(mem_diag.score.miss_rate, abs=1e-12)
        assert sql_diag.prefix_totals_3 == mem_diag.prefix_totals_3
