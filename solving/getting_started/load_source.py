"""Load Welcome Pilgrim and inspect the data RDP has bundled for it."""

from rdp import api

SOURCE_LABEL = "welcome_pilgrim"


def main() -> None:
    """Print the source identity, size, and first few rune indices."""
    source = api.liber_primus.source(SOURCE_LABEL)
    source_data = api.liber_primus.load_source(SOURCE_LABEL)

    print("Source       :", source_data.metadata["display_name"])
    print("Source label :", source.ref["label"])
    print("Rune count   :", len(source_data.ct_idx))
    print("First indices:", list(source_data.ct_idx[:12]))
    print("WLI aligned  :", len(source_data.ct_idx) == len(source_data.wli))


if __name__ == "__main__":
    main()
