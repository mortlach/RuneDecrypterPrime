"""Before solving anything, let's look at the ciphertext we actually have.

RDP contains the Liber Primus transcript and exposes useful parts of it as named
"sources" we can work with.

Welcome Pilgrim is one of those sources. Sources are often labelled by the first
few plaintext words, when those are known, but RDP also has page, line, word and
other ways to locate material. Liber Primus does not give us one wonderfully
convenient naming scheme, so we have to live with a few.

Here we just load the source and inspect it.

The source reference is all we need to pass to a run. Loading the source data
separately lets us inspect the ciphertext, word boundaries and metadata
ourselves.

Nothing is being decrypted yet. We are just checking that we are about to solve
the text we think we are.
"""

from rdp import api


def main() -> None:
    """Load Welcome Pilgrim and print some useful parts of its record."""
    source = api.liber_primus.source("welcome_pilgrim")
    source_data = api.liber_primus.load_source("welcome_pilgrim")

    print("Source       :", source_data.metadata["display_name"])
    print("Source label :", source.ref["label"])
    print("Rune count   :", len(source_data.ct_idx))
    print("First indices:", list(source_data.ct_idx[:12]))
    print("WLI aligned  :", len(source_data.ct_idx) == len(source_data.wli))


if __name__ == "__main__":
    main()
