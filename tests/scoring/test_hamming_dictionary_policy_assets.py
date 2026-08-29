from __future__ import annotations
from rdp import api
from pathlib import Path
from rune_decrypter_prime.core.hamming_dictionary_policy import (
    HammingDictionaryPolicy,
    ensure_hamming_dictionary_policy,
)
from rune_decrypter_prime.scoring.hamming.dictionary_assets import (
    choose_hamming_dictionary_wordlist_dir,
    resolve_hamming_dictionary_wordlist_dir,
)


def test_ensure_hamming_dictionary_policy_normalizes_strings() -> None:
    assert ensure_hamming_dictionary_policy('strict') is HammingDictionaryPolicy.STRICT
    assert ensure_hamming_dictionary_policy(' NORMAL ') is HammingDictionaryPolicy.NORMAL

def test_resolve_hamming_dictionary_wordlist_dir_uses_policy_root() -> None:
    root = Path('assets')
    out = resolve_hamming_dictionary_wordlist_dir(HammingDictionaryPolicy.NORMAL, policy_root=root)
    assert out == root / 'hamming_dictionary_policies/normal/hamming_raw_1g'

def test_choose_hamming_dictionary_wordlist_dir_prefers_explicit_path() -> None:
    explicit = Path('custom/raw1grams')
    out = choose_hamming_dictionary_wordlist_dir(explicit_wordlist_dir=explicit, policy=HammingDictionaryPolicy.STRICT, policy_root=Path('assets'))
    assert out == explicit

def test_scoring_config_serializes_policy_enum_safely() -> None:
    cfg = api.ScoringConfig(
        hamming_dictionary_policy=api.advanced.HammingDictionaryPolicy.STRICT,
        hamming_dictionary_root=Path("assets"),
        span_hamming_assets_dictionary_policy=api.advanced.HammingDictionaryPolicy.NORMAL,
        span_hamming_allow_dictionary_mismatch=True,
    )
    assert cfg.hamming_dictionary_policy is HammingDictionaryPolicy.STRICT
    assert cfg.span_hamming_assets_dictionary_policy is HammingDictionaryPolicy.NORMAL
    dumped = cfg.to_dict()
    assert dumped["hamming_dictionary_policy"] == "strict"
    assert Path(dumped["hamming_dictionary_root"]).as_posix() == "assets"
    assert dumped["span_hamming_assets_dictionary_policy"] == "normal"
    assert dumped["span_hamming_allow_dictionary_mismatch"] is True
