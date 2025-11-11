from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import define_map
from rune_decrypter_prime.api.specs import CipherSpec
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher
from rune_decrypter_prime.backends.xp import have_torch_cuda
from rune_decrypter_prime.core.types import Direction

pytestmark = pytest.mark.tier_a


def _build_cipher_for_spec(spec: CipherSpec, *, key_length: int = 1, device: str = "cpu", length: int = 1):
    cfg = CipherConfig(
        ciphertext=np.zeros(length, dtype=np.uint8),
        wli_data=[[0, length]],
        key_length=int(key_length),
        device=device,
        encoding_dir=Direction.LTR,
        name=spec.kind,
    )
    setattr(cfg, "spec", spec)
    return GenericMapCipher(cfg)


@pytest.mark.parametrize("k", [0, 1, 5, 7, 13, 17, 28])
@pytest.mark.parametrize("ct", [0, 1, 2, 3, 4, 10, 28])
def test_xor_mod29_candidate_counts_and_values(k: int, ct: int):
    N = 29
    spec = define_map(
        N=N,
        function=lambda pt, kk: (pt ^ kk) % N,
        degeneracy="allow",
        resolver="first",
        per_pos_limit=8,
        name="xor-mod29",
    )
    cipher = _build_cipher_for_spec(spec, key_length=1, device="cpu", length=1)

    key = np.array([k], dtype=np.uint8)
    ct_arr = np.array([ct], dtype=np.uint8)

    cands, lens, invalid = cipher.candidates_for(ct_arr, key, limit=spec.per_pos_limit)
    got_len = int(lens[0, 0])
    got_list = cands[0, 0, :got_len].tolist()
    got_invalid = bool(invalid[0, 0])

    brute_pts = [pt for pt in range(N) if ((pt ^ k) % N) == ct]
    brute_pts_sorted = sorted(brute_pts)

    assert got_invalid is (len(brute_pts_sorted) == 0)
    assert got_len == min(len(brute_pts_sorted), spec.per_pos_limit)
    assert got_list == brute_pts_sorted[:got_len]


def test_xor_mod29_explicit_multi_solution_example():
    spec = define_map(
        N=29,
        function=lambda pt, kk: (pt ^ kk) % 29,
        degeneracy="allow",
        resolver="first",
        per_pos_limit=8,
        name="xor-mod29",
    )
    cipher = _build_cipher_for_spec(spec, key_length=1, device="cpu", length=1)

    key = np.array([1], dtype=np.uint8)
    ct_arr = np.array([0], dtype=np.uint8)

    cands, lens, invalid = cipher.candidates_for(ct_arr, key, limit=spec.per_pos_limit)
    got_len = int(lens[0, 0])
    got_list = cands[0, 0, :got_len].tolist()

    assert not bool(invalid[0, 0])
    assert got_len == 2
    assert got_list == [1, 28]


def test_lookup_table_respects_per_pos_limit():
    table = np.zeros((29, 29), dtype=np.uint8)
    spec = define_map(
        N=29,
        table=table,
        degeneracy="allow",
        resolver="first",
        per_pos_limit=1,
        name="zero-table",
    )
    cipher = _build_cipher_for_spec(spec, key_length=1, device="cpu", length=1)

    key = np.array([0], dtype=np.uint8)
    ct_arr = np.array([0], dtype=np.uint8)

    cands, lens, invalid = cipher.candidates_for(ct_arr, key, limit=spec.per_pos_limit)
    assert int(lens[0, 0]) == 1
    assert cands[0, 0, 0] == 0
    assert not bool(invalid[0, 0])


@pytest.mark.skipif(not have_torch_cuda(), reason="CUDA not available")
def test_candidates_match_on_cuda():
    spec = define_map(
        N=29,
        function=lambda pt, kk: (pt + kk) % 29,
        degeneracy="allow",
        resolver="first",
        per_pos_limit=4,
        name="add-mod29",
    )
    cpu_cipher = _build_cipher_for_spec(spec, key_length=1, device="cpu", length=4)
    cuda_cipher = _build_cipher_for_spec(spec, key_length=1, device="cuda", length=4)

    key = np.array([3], dtype=np.uint8)
    ct_arr = np.array([0, 1, 2, 3], dtype=np.uint8)
    limit = spec.per_pos_limit

    cpu_cands, cpu_lens, cpu_invalid = cpu_cipher.candidates_for(ct_arr, key, limit=limit)
    cuda_cands, cuda_lens, cuda_invalid = cuda_cipher.candidates_for(ct_arr, key, limit=limit)

    assert np.array_equal(cpu_cands, cuda_cands)
    assert np.array_equal(cpu_lens, cuda_lens)
    assert np.array_equal(cpu_invalid, cuda_invalid)
