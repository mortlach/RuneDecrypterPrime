from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from importlib import resources
from types import SimpleNamespace

import pytest

from rdp import api
from rdp.data.liber_primus import lp_solved_plaintext
from rdp.data.liber_primus.lp_source_catalogue import (
    SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
    resolve_source_label,
)
from rdp.data.runeglish import Runeglish


pytestmark = pytest.mark.tier_a

# Counts and semantic hashes come from the independently validated user-supplied
# dump, including the source-verified Some Wisdom magic-square words.
# Line wrapping and newline encoding in the presentation files are not data.
# Semantic hashes cover indices plus exact word-length information; rune hashes
# independently cover the flattened supplied rune arrays.
EXPECTED = {
    "warning": (
        "red_rune.warning",
        "warning.txt",
        45,
        184,
        "853c1fe69a8b96ddee4bf3f896d8c5cfed76b6330e8dc822ccd3a0f53c81882a",
        "c20d5cad4734ee41ecc992ae2fafc110405f5366bf1fa1ebfebe9d28179c3460",
    ),
    "some_wisdom": (
        "red_rune.some_wisdom",
        "some_wisdom.txt",
        31,
        157,
        "28c20b1c3d685504c18a4ee2929dabc3ef1fab294f66e5075b2d49d822dfb75d",
        "6d34dc722558502375b256829c6ebac3ab4fd36db3322c97e51b30f87968ca07",
    ),
    "welcome_pilgrim": (
        "red_rune.welcome_pilgrim",
        "welcome_pilgrim.txt",
        124,
        515,
        "82c1fa5265ffed1c3480df4543cbcb1bb02abd585c52e7aca7e49b5caf265398",
        "0d40810fc02a57bc30eaa0d85f2a78a987b85fe2ac04afa9bba14bd492fc86d0",
    ),
    "koan_a_man": (
        "red_rune.koan_a_man",
        "koan_a_man.txt",
        208,
        778,
        "4f4ed2dad440bcfa232b5e56af9b08863471fcc347ef9e02ae60902c452c4155",
        "59917f477040b6196b670df9b07559e81703b33963a12751061b84ddd49823c5",
    ),
    "loss_of_divinity": (
        "red_rune.loss_of_divinity",
        "loss_of_divinity.txt",
        181,
        755,
        "b8e2923f32cf53901a107ed7c4e738d81e1ca35f5d4b519931cf2b1817e7c742",
        "b4c81a1fb34f890f6a2534a701782501fccc1cc1249c1353c17dabafc68896f0",
    ),
    "koan_during_lesson": (
        "red_rune.koan_during_lesson",
        "koan_during_lesson.txt",
        87,
        319,
        "9b78d4c2a1b40483db322697f3b8a084f7da085c197fbfaf313c242100cac376",
        "e67cc38e4567c0be37360804b7cff2c7ac7e6138e6b01a4c34923288cb89b8a0",
    ),
    "instruction": (
        "red_rune.instruction",
        "instruction.txt",
        18,
        89,
        "d6869f765301162f787e263033147fff7eb78d8c9b15ea3f1bed22235a4a0ab0",
        "8b42909a73bf2873dc13dea618cd7e12b594606f44bc556d1aa1881128ddea3d",
    ),
    "an_end": (
        "red_rune.an_end",
        "an_end.txt",
        25,
        85,
        "4356d8c43bb9218fb6b75dfc11159933f7b77d6e7612813b79c78e732dff6e43",
        "9f94fa76136eb8d6c23f3e8aed540aefc27971fab2dd427f3b714db5f85cda51",
    ),
    "parable": (
        "red_rune.parable",
        "parable.txt",
        20,
        95,
        "d8abec2a60b387aabec45402f69a2c2c71d26f0bb6700f602c1928518b6e632e",
        "03561957c3cda8729d773fd6986d30d4bb3e74d84501a6e28e897d4783dfa0ff",
    ),
}


@pytest.mark.parametrize("label,expected", EXPECTED.items())
def test_every_solved_plaintext_matches_the_supplied_data(
    label: str,
    expected: tuple[str, str, int, int, str, str],
) -> None:
    canonical_label, filename, word_count, rune_count, semantic_hash, rune_hash = expected
    entry = resolve_source_label(label)
    reference = api.liber_primus.load_plaintext(label)

    assert entry.source_status == SOURCE_STATUS_SOLVED_TEXT_AVAILABLE
    assert entry.solved_plaintext_file == filename
    assert reference.source_label == canonical_label
    assert reference.metadata["source_label"] == canonical_label
    assert reference.metadata["resource_file"] == filename
    assert reference.metadata["word_count"] == word_count
    assert reference.metadata["rune_count"] == rune_count
    assert (
        len(reference.indices) == len(reference.word_length_information) == rune_count
    )
    assert (
        sum(position == 0 for position, _length in reference.word_length_information)
        == word_count
    )

    resource = (
        resources.files("rdp.data.liber_primus")
        .joinpath("solved_plaintext")
        .joinpath(filename)
    )
    raw = resource.read_bytes()

    tokens = [
        token
        for word in raw.decode("utf-8").split()
        for token in word.split("·")
    ]
    assert all(token in Runeglish.latin_canon for token in tokens)
    assert len(tokens) == rune_count
    semantic_payload = json.dumps(
        {
            "indices": list(reference.indices),
            "word_length_information": [
                list(item) for item in reference.word_length_information
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(semantic_payload).hexdigest() == semantic_hash
    assert Runeglish.to_delimited_rune_latin(
        reference.indices,
        reference.word_length_information,
    ) == reference.rune_latin
    assert Runeglish.to_rune(
        reference.indices,
        reference.word_length_information,
    ) == reference.runes
    flattened_runes = reference.runes.replace(" ", "").encode("utf-8")
    assert hashlib.sha256(flattened_runes).hexdigest() == rune_hash

    reparsed = lp_solved_plaintext._parse_canonical_rune_latin(
        reference.rune_latin,
        source_label=canonical_label,
    )
    assert reparsed == (
        reference.indices,
        reference.word_length_information,
        reference.rune_latin,
    )


@pytest.mark.parametrize("label", ["some_wisdom", "loss_of_divinity"])
def test_unenciphered_solved_plaintext_matches_the_complete_source(label: str) -> None:
    source = api.liber_primus.load_source(label)
    reference = api.liber_primus.load_plaintext(label)
    assert reference.indices == tuple(source.ct_idx)
    assert reference.word_length_information == tuple(map(tuple, source.wli))


@pytest.mark.parametrize("label", EXPECTED)
def test_every_existing_alias_loads_the_same_plaintext(label: str) -> None:
    entry = resolve_source_label(label)
    reference = api.liber_primus.load_plaintext(label)
    for alias in (entry.source_label, *entry.aliases):
        assert api.liber_primus.load_plaintext(alias) == reference


@pytest.mark.parametrize("label,expected", EXPECTED.items())
def test_presentation_whitespace_does_not_change_solved_plaintext(
    label: str,
    expected: tuple[str, str, int, int, str, str],
) -> None:
    canonical_label, filename, *_rest = expected
    resource = (
        resources.files("rdp.data.liber_primus")
        .joinpath("solved_plaintext")
        .joinpath(filename)
    )
    words = resource.read_text(encoding="utf-8").split()
    reference = api.liber_primus.load_plaintext(label)

    presentations = (
        " ".join(words),
        "\r\n".join(words) + "\r\n",
        "\n".join(
            "\t".join(words[index : index + 7])
            for index in range(0, len(words), 7)
        ),
    )
    for presentation in presentations:
        assert lp_solved_plaintext._parse_canonical_rune_latin(
            presentation,
            source_label=canonical_label,
        ) == (
            reference.indices,
            reference.word_length_information,
            reference.rune_latin,
        )


@pytest.mark.parametrize("token", ("NG", "ING", "K", "V", "Z", "IA"))
def test_controlled_plaintext_parser_rejects_loose_runeglish_aliases(
    token: str,
) -> None:
    with pytest.raises(ValueError, match="non-canonical RuneLatin token"):
        lp_solved_plaintext._parse_canonical_rune_latin(
            token,
            source_label="red_rune.test",
        )


def test_plaintext_data_is_immutable() -> None:
    reference = api.liber_primus.load_plaintext("warning")
    with pytest.raises(FrozenInstanceError):
        reference.source_label = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        reference.metadata["source_label"] = "changed"  # type: ignore[index]


def test_unknown_and_known_unsolved_labels_fail_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(KeyError, match="unknown LP source label"):
        api.liber_primus.load_plaintext("not_a_real_source")

    unsolved = SimpleNamespace(
        source_label="red_rune.unsolved",
        display_name="Unsolved",
        solved_plaintext_file=None,
    )
    monkeypatch.setattr(
        lp_solved_plaintext,
        "resolve_source_label",
        lambda _label: unsolved,
    )
    with pytest.raises(
        ValueError,
        match="no solved plaintext is available for LP source 'red_rune.unsolved'",
    ):
        api.liber_primus.load_plaintext("unsolved")


def test_plaintext_loader_stays_in_the_lp_namespace() -> None:
    assert "load_plaintext" in api.liber_primus.__all__
    assert not hasattr(api, "load_plaintext")
