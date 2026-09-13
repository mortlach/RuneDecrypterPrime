"""Run the prepared Welcome Pilgrim search and inspect its public result."""

from rdp import api

from solving.getting_started.prepare_search import build_request


def main() -> None:
    """Execute the longer search and print its main structured fields."""
    result = api.run(build_request())

    print("Status            :", result.status)
    print("Score             :", result.score)
    print("Key               :", result.key)
    print("Plaintext indices :", result.plaintext_indices)
    print("Plaintext runes   :", result.plaintext_runes)
    print("Plaintext RuneLatin:", result.plaintext_rune_latin)
    print("Reading RuneLatin :", result.plaintext_reading_rune_latin)


if __name__ == "__main__":
    main()
