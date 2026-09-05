# ruff: noqa: N999
"""Load a named Liber Primus source through the public data boundary.

Source selection, solve recipe, known truth and solver result are separate
objects.  This stop loads only the first of them so the boundary is unmistakable.
"""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"
TEXT_DIRECTION = api.TextDirection.RIGHT_TO_LEFT


def main() -> None:
    # A stable label asks RDP's public LP namespace for reviewed ciphertext,
    # word locations and provenance metadata.  It avoids embedding a local file
    # path or silently selecting a page fragment in the example.
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
    print("Known truth  : source status only; not supplied to a solver")
    print("Solver result: none")
    print("Boundary     : source data loaded")
    print("Where next   : examples/lp_welcome_pilgrim_solve.py")

    # These checks protect source identity and alignment.  They say nothing
    # about a cipher hypothesis because no solve recipe has been constructed.
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
