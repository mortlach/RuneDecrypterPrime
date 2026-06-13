from __future__ import annotations

from pathlib import Path

from rune_decrypter_prime.core.hamming_dictionary_policy import (
    HammingDictionaryPolicy,
    ensure_hamming_dictionary_policy,
)


_POLICY_REL_DIRS = {
    HammingDictionaryPolicy.STRICT: Path("hamming_dictionary_policies/strict/hamming_raw_1g"),
    HammingDictionaryPolicy.NORMAL: Path("hamming_dictionary_policies/normal/hamming_raw_1g"),
    HammingDictionaryPolicy.BROAD: Path("hamming_dictionary_policies/broad/hamming_raw_1g"),
    HammingDictionaryPolicy.RESEARCH: Path("hamming_dictionary_policies/research/hamming_raw_1g"),
}


def resolve_hamming_dictionary_wordlist_dir(
    policy: HammingDictionaryPolicy | str,
    *,
    policy_root: str | Path | None,
) -> Path | None:
    if policy_root is None:
        return None
    resolved_policy = ensure_hamming_dictionary_policy(policy)
    return Path(policy_root) / _POLICY_REL_DIRS[resolved_policy]


def choose_hamming_dictionary_wordlist_dir(
    *,
    explicit_wordlist_dir: str | Path | None,
    policy: HammingDictionaryPolicy | str,
    policy_root: str | Path | None,
) -> Path | None:
    if explicit_wordlist_dir is not None:
        return Path(explicit_wordlist_dir)
    return resolve_hamming_dictionary_wordlist_dir(policy, policy_root=policy_root)


__all__ = [
    "choose_hamming_dictionary_wordlist_dir",
    "resolve_hamming_dictionary_wordlist_dir",
]
