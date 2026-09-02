from __future__ import annotations
import csv
from pathlib import Path
import pytest
from rdp.core.types import Direction
from rune_decrypter_prime.data.wordlists.loaders import default_wordlists_dir, load_short_word_csv, load_word_crib_config_from_csv

def test_load_short_word_csv_reads_counts():
    table = load_short_word_csv(length=1, direction=Direction.LTR)
    assert 'A' in table and table['A'] > 0
    assert 'I' in table and table['I'] > 0

def test_load_short_word_csv_validates_indices(tmp_path: Path):
    path = tmp_path / 'short_words_ltr_len1.csv'
    with path.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['latin_word', 'rune_word', 'rune_indices', 'weight'])
        writer.writerow(['A', 'X', '0', '1'])
    with pytest.raises(ValueError):
        load_short_word_csv(length=1, direction=Direction.LTR, base_dir=tmp_path)

def test_load_word_crib_config_from_csv():
    cfg = load_word_crib_config_from_csv(direction=Direction.LTR, lengths=(1,))
    assert cfg.enabled is True
    assert 1 in cfg.short_word_dict
    assert 'A' in cfg.short_word_dict[1] and cfg.short_word_dict[1]['A'] > 0

def test_short_word_csv_has_consistent_lengths():
    base = default_wordlists_dir()
    for direction in ('ltr', 'rtl'):
        for length in (1, 2, 3):
            path = base / f'short_words_{direction}_len{length}.csv'
            assert path.is_file(), f'Missing CSV {path}'
            with path.open('r', encoding='utf-8', newline='') as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    indices = row.get('rune_indices', '')
                    tokens = [tok for tok in indices.split() if tok]
                    assert len(tokens) == length, f'Row {row} in {path} expected {length} rune indices, got {tokens}'
