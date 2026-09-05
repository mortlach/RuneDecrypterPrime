# ruff: noqa: N999
"""Encrypt and decrypt one reviewed rune message with a known key."""

from rdp import api

# RDP's cipher boundary uses rune indices.  The three forms are kept together
# here so the fixture can be checked without hiding a transliteration step.
LATIN_TEXT = "FOLLOW THE EVIDENCE"
RUNE_TEXT = "ᚠᚩᛚᛚᚩᚹ ᚦᛖ ᛖᚢᛁᛞᛖᚾᚳᛖ"
PLAINTEXT = (0, 3, 20, 20, 3, 7, 2, 18, 18, 1, 10, 23, 18, 9, 5, 18)
KEY: api.ConcreteKey = (3, 1, 4)


def main() -> None:
    cipher = api.CipherSpec.vigenere()
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=KEY)
    recovered = api.decrypt(ciphertext, cipher=cipher, key=KEY)

    print("Known-key round trip")
    print("Latin reference :", LATIN_TEXT)
    print("Rune reference  :", RUNE_TEXT)
    print("Plaintext       :", PLAINTEXT)
    print("Key             :", KEY)
    print("Ciphertext      :", ciphertext)
    print("Recovered       :", recovered)

    if recovered != PLAINTEXT:
        raise AssertionError("decrypt(encrypt(plaintext)) changed the message")


if __name__ == "__main__":
    main()
