# ruff: noqa: N999
"""Encrypt and decrypt one reviewed rune message with a known key.

This first stop separates a known-key operation from a search.  Nothing is
being inferred: the cipher, key and plaintext are all supplied explicitly.
"""

from rdp import api

# RDP's cipher boundary uses rune indices.  Latin and visible runes are useful
# to a reader, but the numeric sequence is the value transformed by the cipher.
# All three reviewed forms are kept together here so no transliteration step is
# hidden inside the example.
LATIN_TEXT = "FOLLOW THE EVIDENCE"
RUNE_TEXT = "ᚠᚩᛚᛚᚩᚹ ᚦᛖ ᛖᚢᛁᛞᛖᚾᚳᛖ"
# fmt: off
PLAINTEXT = (
    0, 3, 20, 20, 3, 7, 2, 18, 18, 1, 10, 23, 18, 9,
    5, 18,
)
# fmt: on
KEY: api.ConcreteKey = (3, 1, 4)


def main() -> None:
    # A CipherSpec identifies the transformation and its fixed parameters.  It
    # does not contain the key and it does not ask a solver to find anything.
    cipher = api.CipherSpec.vigenere()

    # A concrete key is the actual key used by a known-key operation.  Later
    # examples use KeySpec instead: that describes a space of possible keys for
    # a solver to search.
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=KEY)
    recovered = api.decrypt(ciphertext, cipher=cipher, key=KEY)

    print("Known-key round trip")
    print("Latin reference :", LATIN_TEXT)
    print("Rune reference  :", RUNE_TEXT)
    print("Plaintext       :", PLAINTEXT)
    print("Key             :", KEY)
    print("Ciphertext      :", ciphertext)
    print("Recovered       :", recovered)

    # The assertion is the scientific claim made by this file: applying the
    # known inverse returns exactly the original rune indices.
    if recovered != PLAINTEXT:
        raise AssertionError("decrypt(encrypt(plaintext)) changed the message")


if __name__ == "__main__":
    main()
