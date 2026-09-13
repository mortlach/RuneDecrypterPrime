# ruff: noqa: N999
"""Load Welcome Pilgrim from the bundled Liber Primus data."""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"


def main() -> None:
    source = api.liber_primus.source(SOURCE_LABEL)

    print("Liber Primus source")
    print("Source kind      :", source.source_kind)
    print("Source label     :", source.ref["label"])
    print("Transcript asset :", source.asset_id)
    print("Transcript version:", source.asset_version)

    # A source reference records identity. The run loads its ciphertext and WLI.
    expected_boundary = (
        source.source_kind == "liber_primus.label"
        and source.ref["label"] == "red_rune.welcome_pilgrim"
        and source.asset_id == "liber_primus.main_transcript"
    )
    if not expected_boundary:
        raise AssertionError("the named Liber Primus source reference changed")


if __name__ == "__main__":
    main()
