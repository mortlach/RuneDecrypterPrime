# ruff: noqa: N999
"""Load Welcome Pilgrim from the bundled Liber Primus data.

We've used constructed messages so far. Now let's load a real source and
look at what RDP provides before deciding how to search it.
"""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"
TEXT_DIRECTION = api.TextDirection.RIGHT_TO_LEFT


def main() -> None:
    # Use the source label to select Welcome Pilgrim. The payload contains its
    # rune numbers, word positions and information about where the text came
    # from. We don't need to find a local transcript file ourselves.
    payload = api.liber_primus.payload_from_label(SOURCE_LABEL)
    metadata = payload.metadata

    print("Liber Primus source")
    print("Display name :", metadata["display_name"])
    print("Source label :", metadata["source_label"])
    print("Source status:", metadata["source_status"])
    print("Text direction:", TEXT_DIRECTION.value)
    print("Rune count   :", len(payload.ct_idx))
    print("Index preview:", tuple(payload.ct_idx[:12]))
    print("Solve recipe : not loaded")
    print("Known answer : not used; this file only loads the source")
    print("Solver result: none")
    print("Loaded       : ciphertext and word information")
    print("Where next   : examples/lp_welcome_pilgrim_solve.py")

    # Check that we loaded the expected source and that its rune and word
    # information line up. We haven't asked RDP to decrypt anything yet.
    expected_boundary = (
        metadata["display_name"] == "Welcome Pilgrim"
        and metadata["source_label"] == "red_rune.welcome_pilgrim"
        and metadata["source_status"] == "solved_text_available"
        and len(payload.ct_idx) == len(payload.wli) == 515
        and tuple(payload.ct_idx[:12]) == (1, 28, 21, 15, 12, 0, 5, 4, 12, 1, 6, 13)
    )
    if not expected_boundary:
        raise AssertionError("the named Liber Primus source boundary changed")


if __name__ == "__main__":
    main()
