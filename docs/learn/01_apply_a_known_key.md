# Apply a known key

Start with the smallest useful RDP operation: decrypt some rune indices with a
known key.

If the terminology is unfamiliar, see
[Words used in the learning examples](00_words_used_here.md).

Liber Primus uses a 29-rune alphabet.

RDP performs the cipher maths by representing each rune as one number from `0`
to `28`.

So this:

```python
ciphertext = (5, 8, 11, 14, 17, 20)
```

means:

> six ciphertext runes, represented by their rune indices.

It is not six decimal digits hidden in the book.

Now decrypt them:

```python
from rdp import api

ciphertext = (5, 8, 11, 14, 17, 20)

plaintext = api.decrypt(
    ciphertext,
    cipher=api.CipherSpec.vigenere(),
    key=(3,),
)

print(plaintext)
```

There is no solver here.

You supplied:

```text
ciphertext  the encrypted rune indices
cipher      Vigenere
key         (3,)
```

so RDP simply applies that cipher with that known key.

The returned plaintext is also a tuple of rune indices.

Known-key operations are useful for checking that a cipher transformation does
what you think it does before adding a search around it.

Next: [Search a key](02_search_a_key.md).
