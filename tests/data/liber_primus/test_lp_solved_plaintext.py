from __future__ import annotations

import hashlib
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

# Counts and hashes come from the independently validated user-supplied dump.
# Rune hashes cover the flattened supplied rune arrays, not the formatted files.
EXPECTED = {
    "warning": (
        "red_rune.warning",
        "warning.txt",
        45,
        184,
        "0cd840a9c30e22f094ca7f8750803cf7ad20cee5304873d25ac620732229cd76",
        "c20d5cad4734ee41ecc992ae2fafc110405f5366bf1fa1ebfebe9d28179c3460",
    ),
    "some_wisdom": (
        "red_rune.some_wisdom",
        "some_wisdom.txt",
        18,
        81,
        "b92b540cc8062f648678f8b6d7a883bba9a392ac133824cdc2ce254c45366a40",
        "7d156f190410f2ff8bb61f31591a34991084c19910b669539970615786997d29",
    ),
    "welcome_pilgrim": (
        "red_rune.welcome_pilgrim",
        "welcome_pilgrim.txt",
        124,
        515,
        "9ccdc80085da1483a5e87bcb65ed1df65ba2cd3be253da3691b65b748e337b39",
        "0d40810fc02a57bc30eaa0d85f2a78a987b85fe2ac04afa9bba14bd492fc86d0",
    ),
    "koan_a_man": (
        "red_rune.koan_a_man",
        "koan_a_man.txt",
        208,
        778,
        "4c97b4637b4788d2bba87bc0f4ef0cf74b3699e98f5d7edeb70fc4b971c2708c",
        "59917f477040b6196b670df9b07559e81703b33963a12751061b84ddd49823c5",
    ),
    "loss_of_divinity": (
        "red_rune.loss_of_divinity",
        "loss_of_divinity.txt",
        181,
        755,
        "75cad3c778dcaf8c188a0074e95c45d87f3754512a7b36e0dee16f10a074b031",
        "b4c81a1fb34f890f6a2534a701782501fccc1cc1249c1353c17dabafc68896f0",
    ),
    "koan_during_lesson": (
        "red_rune.koan_during_lesson",
        "koan_during_lesson.txt",
        87,
        319,
        "28fe5bb102fa0829834ef85e4e7702e52d2d07d1303baf9d3da7fbb7c3a1b0cd",
        "e67cc38e4567c0be37360804b7cff2c7ac7e6138e6b01a4c34923288cb89b8a0",
    ),
    "instruction": (
        "red_rune.instruction",
        "instruction.txt",
        18,
        89,
        "989a06842f1ac0fe76985c0bf44f2f00b1b405974e148dd3b4b309f17199dc6a",
        "8b42909a73bf2873dc13dea618cd7e12b594606f44bc556d1aa1881128ddea3d",
    ),
    "an_end": (
        "red_rune.an_end",
        "an_end.txt",
        25,
        85,
        "63f2344a6bb5e6bed7677dbe5f53eb066bc02b6ca11df71402f05f50c8b9bc57",
        "9f94fa76136eb8d6c23f3e8aed540aefc27971fab2dd427f3b714db5f85cda51",
    ),
    "parable": (
        "red_rune.parable",
        "parable.txt",
        20,
        95,
        "a4e2aa7d2cc9a11f68358204fab4bfdf2f5bcade594f7d6f853a280f535a5a05",
        "03561957c3cda8729d773fd6986d30d4bb3e74d84501a6e28e897d4783dfa0ff",
    ),
}


@pytest.mark.parametrize("label,expected", EXPECTED.items())
def test_every_solved_plaintext_matches_the_supplied_data(
    label: str,
    expected: tuple[str, str, int, int, str, str],
) -> None:
    canonical_label, filename, word_count, rune_count, file_hash, rune_hash = expected
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
    assert hashlib.sha256(raw).hexdigest() == file_hash

    tokens = [
        token
        for word in raw.decode("utf-8").split()
        for token in word.split("·")
    ]
    assert all(token in Runeglish.latin_canon for token in tokens)
    assert len(tokens) == rune_count
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


@pytest.mark.parametrize("label", EXPECTED)
def test_every_existing_alias_loads_the_same_plaintext(label: str) -> None:
    entry = resolve_source_label(label)
    reference = api.liber_primus.load_plaintext(label)
    for alias in (entry.source_label, *entry.aliases):
        assert api.liber_primus.load_plaintext(alias) == reference


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
