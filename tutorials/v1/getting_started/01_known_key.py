# ruff: noqa: N999
"""Encrypt a message, then decrypt it with the same key.

Before trying to find an unknown key, let's use one we already know.
We should get our original message back.
"""

from rdp import api

# RDP works with 29 runes, numbered from 0 to 28.
# Here is our message in English, in runes, and as those numbers.
# The encrypt/decrypt functions take the numbers; the other two lines are here
# so we can read what we're working with.
LATIN_TEXT = "FOLLOW THE EVIDENCE"
RUNE_TEXT = "ᚠᚩᛚᛚᚩᚹ ᚦᛖ ᛖᚢᛁᛞᛖᚾᚳᛖ"
# fmt: off
PLAINTEXT = (
    0, 3, 20, 20, 3, 7, 2, 18, 18, 1, 10, 23, 18, 9,
    5, 18,
)
# fmt: on
# Our key contains three values. Vigenere repeats them along the message:
# 3, 1, 4, 3, 1, 4, ...
#
# ConcreteKey simply means we have the actual key values.
# When we start searching, we'll use KeySpec to describe the possible
# keys instead.
KEY: api.ConcreteKey = (3, 1, 4)


def main() -> None:
    # CipherSpec tells RDP which cipher to use.
    # We'll use Vigenere: add each key value to the corresponding rune number,
    # wrapping around modulo 29.
    #
    # Other choices include substitution, rail fence and columnar
    # transposition. Each needs a suitable kind of key.
    cipher = api.CipherSpec.vigenere()

    # Encrypt our message, then use the same key to decrypt it.
    # There is no search involved here—we supplied the key ourselves.
    ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=KEY)
    recovered = api.decrypt(ciphertext, cipher=cipher, key=KEY)

    print("Known-key round trip")
    print("Latin reference :", LATIN_TEXT)
    print("Rune reference  :", RUNE_TEXT)
    print("Plaintext       :", PLAINTEXT)
    print("Key             :", KEY)
    print("Ciphertext      :", ciphertext)
    print("Recovered       :", recovered)

    # We should have exactly the message we started with.
    if recovered != PLAINTEXT:
        raise AssertionError("decrypt(encrypt(plaintext)) changed the message")

    # Try changing one key value and running this again.
    # The ciphertext will change, but we should still recover our message
    # because both operations use the same key.


if __name__ == "__main__":
    main()
