from __future__ import annotations
from pathlib import Path
from rdp.data.liber_primus.lp_main import default_main_transcript_path
from rune_decrypter_prime.data.wordlists.loaders import default_wordlists_dir
from rune_decrypter_prime.scoring.hamming.loader import default_hamming_dir
from rune_decrypter_prime.scoring.language_model.paths import default_lm_root

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _assert_under_assets(path: Path, *, expected_suffix: str) -> None:
    root = _repo_root()
    rel = path.resolve().relative_to(root)
    rel_posix = rel.as_posix()
    assert rel_posix.startswith('assets/'), f'default path must be under assets/: {rel_posix}'
    assert rel_posix.endswith(expected_suffix), f'unexpected default suffix: {rel_posix}'

def test_language_model_default_root_under_assets():
    _assert_under_assets(default_lm_root(), expected_suffix='language_model/lmp')

def test_hamming_default_root_under_assets():
    _assert_under_assets(default_hamming_dir(), expected_suffix='hamming_raw_1g')

def test_wordlists_default_root_under_assets():
    _assert_under_assets(default_wordlists_dir(), expected_suffix='wordlists')

def test_lp_main_transcript_default_under_assets():
    _assert_under_assets(default_main_transcript_path(), expected_suffix='liber_primus/liber-primus__transcription--master.txt')
