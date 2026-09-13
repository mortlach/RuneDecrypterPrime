# Known-key encrypt and decrypt

When the key is already known, use:

```python
api.encrypt(...)
api.decrypt(...)
```

For example:

```python
from rdp import api

plaintext: api.RuneIndices = (0, 1, 2, 3, 4, 5)
key: api.ConcreteKey = (3, 1, 4)

cipher = api.CipherSpec.vigenere()

ciphertext = api.encrypt(
    plaintext,
    cipher=cipher,
    key=key,
)

recovered = api.decrypt(
    ciphertext,
    cipher=cipher,
    key=key,
)
```

The key is a `ConcreteKey`, which is a tuple of integers.

A solver and key space are only needed when the key is unknown.

## Where known-key operations fit

Known-key operations are useful for:

- checking a cipher implementation
- constructing a controlled test problem
- replaying a known transformation
- verifying that encryption and decryption agree

They do not use the solver or scorer.

For unknown keys, move to [Building a run](../guides/building_a_run.md) and
[Keys and key spaces](../guides/keyops.md).

`tutorials/v1/getting_started/01_known_key.py` is the first runnable example.
See [Tutorials and examples](../tutorials/README.md).
