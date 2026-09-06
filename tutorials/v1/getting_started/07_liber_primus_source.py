# ruff: noqa: N999
"""Load Welcome Pilgrim from the bundled Liber Primus data."""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"


def main() -> None:
    payload = api.liber_primus.payload_from_label(SOURCE_LABEL)
    metadata = payload.metadata

    print("Liber Primus source")
    print("Display name :", metadata["display_name"])
    print("Source label :", metadata["source_label"])
    print("Source status:", metadata["source_status"])
    print("Rune count   :", len(payload.ct_idx))
    print("Index preview:", tuple(payload.ct_idx[:12]))

    # This tutorial checks source loading only. It does not run a solver.
    expected_boundary = (
        metadata["display_name"] == "Welcome Pilgrim"
        and metadata["source_label"] == "red_rune.welcome_pilgrim"
        and metadata["source_status"] == "solved_text_available"
        and len(payload.ct_idx) == len(payload.wli) == 515
        and tuple(payload.ct_idx[:12])
        == (1, 28, 21, 15, 12, 0, 5, 4, 12, 1, 6, 13)
    )
    if not expected_boundary:
        raise AssertionError("the named Liber Primus source boundary changed")


if __name__ == "__main__":
    main()
