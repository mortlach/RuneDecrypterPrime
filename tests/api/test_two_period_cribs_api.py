from __future__ import annotations

import pytest
import numpy as np

from rune_decrypter_prime import api
from rune_decrypter_prime.api.two_period_cribs import normalize_two_period_cribs_request
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.utils.runeglish import Runeglish


def test_builder_is_canonical_and_json_safe():
    spec = api.SolverSpec.two_period_cribs(
        fixed_cribs=(("Uncomfortable", 188),),
        candidate_words=("pilgrimage", "Dormouse", "dormouse"),
        candidate_positions={"dormouse": (206, 81, 206)},
        starts=7,
        seed=2026,
    )
    request = normalize_two_period_cribs_request(spec)
    assert spec.name == "two_period_cribs"
    assert spec.seed == 2026
    assert spec.params["fixed_cribs"] == [["uncomfortable", 188]]
    assert spec.params["candidate_words"] == ["dormouse", "pilgrimage"]
    assert spec.params["candidate_positions"] == {"dormouse": [81, 206]}
    assert request.effective_seed == 2026


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"fixed_cribs": "word"}, TypeError),
        ({"fixed_cribs": (("bad word", 0),)}, ValueError),
        ({"fixed_cribs": (("word", True),)}, TypeError),
        ({"candidate_words": "word"}, TypeError),
        ({"candidate_words": ("word",), "candidate_positions": {"other": (0,)}}, ValueError),
        ({"candidate_words": ("word",), "candidate_positions": {"word": "0"}}, TypeError),
        ({"fixed_cribs": (("word", 0),), "starts": 0}, ValueError),
        ({}, ValueError),
    ],
)
def test_builder_rejects_invalid_contracts(kwargs, error):
    with pytest.raises(error):
        api.SolverSpec.two_period_cribs(**kwargs)


def test_special_route_blocks_latin_before_search():
    cipher, key = api.by_name.cipher_with_key(
        "two_period_vigenere", period_a=5, period_b=7, default_key=True
    )
    solver = api.SolverSpec.two_period_cribs(fixed_cribs=(("word", 0),), starts=1)
    with pytest.raises(ValueError, match="rune ciphertext"):
        api.run(text="latin words", cipher=cipher, key=key, solver=solver)


def test_real_route_returns_standard_exact_solution_with_installed_assets():
    from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1

    word_starts = [index for index, pair in enumerate(word_breaks1) if int(pair[0]) == 0]
    word_ends = {
        index + 1
        for index, pair in enumerate(word_breaks1)
        if int(pair[0]) == int(pair[1]) - 1
    }
    sample_start = next(index for index in word_starts if index + 308 in word_ends)
    plaintext = np.asarray(plaintext1[sample_start:sample_start + 308], dtype=np.uint8)
    wli = tuple(
        tuple(int(x) for x in pair)
        for pair in word_breaks1[sample_start:sample_start + 308]
    )
    fixed_cribs = []
    for start, (offset, length) in enumerate(wli):
        if offset != 0:
            continue
        tokens = []
        for value in plaintext[start:start + length]:
            token = Runeglish.pos2latin[int(value)]
            tokens.append("ING" if token == "(I)NG" else token)
        word = "".join(tokens).lower()
        encoded, _encoded_wli, _runes = Runeglish.encode_english_to_runes(
            word, direction="ltr"
        )
        if encoded == plaintext[start:start + length].astype(int).tolist():
            fixed_cribs.append((word, start))

    cipher, key = api.by_name.cipher_with_key(
        "two_period_vigenere", period_a=13, period_b=31, default_key=True
    )
    known_key = np.asarray(
        [*((5 * index + 3) % 29 for index in range(13)), 0,
         *((7 * index + 11) % 29 for index in range(1, 31))],
        dtype=np.uint8,
    )
    cipher_obj = api.cipher_instance(cipher)
    ciphertext = cipher_obj.encrypt_single(plaintext=plaintext, key=known_key)
    solver = api.SolverSpec.two_period_cribs(
        fixed_cribs=tuple(fixed_cribs), starts=1, seed=2026
    )
    result = api.run(
        text=(ciphertext, wli),
        cipher=cipher,
        key=key,
        solver=solver,
        encoding_dir=Direction.LTR,
        return_solver_report=True,
    )

    assert isinstance(result, api.RunResult)
    assert result.solution.key == known_key.astype(int).tolist()
    assert result.solution.plaintext_idx == plaintext.astype(int).tolist()
    assert result.solution.stop_reason == "done"
    assert result.solver_report.solver_name == "two_period_cribs"
    assert result.solver_report.details["execution_route"] == "two_period_cribs"
