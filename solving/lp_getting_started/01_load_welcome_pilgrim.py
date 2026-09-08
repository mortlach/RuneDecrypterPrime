"""Start with the text we actually have.

Welcome Pilgrim is a named source in the LP catalogue. The source reference
is enough to start a run; the loaded source lets us inspect the rune indices
and word boundaries first. Nothing has been decrypted at this point.
"""

from rdp import api


def main() -> None:
    """Inspect the source and check that each rune has a WLI pair."""
    source = api.liber_primus.source("welcome_pilgrim")
    source_data = api.liber_primus.load_source("welcome_pilgrim")

    print("Source       :", source_data.metadata["display_name"])
    print("Source label :", source.ref["label"])
    print("Rune count   :", len(source_data.ct_idx))
    print("First indices:", list(source_data.ct_idx[:12]))
    print("WLI aligned  :", len(source_data.ct_idx) == len(source_data.wli))


if __name__ == "__main__":
    main()
