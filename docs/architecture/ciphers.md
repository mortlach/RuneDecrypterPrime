# Ciphers

Ciphers are reversible mappings over the rune alphabet. Public callers describe
them with immutable `api.CipherSpec` values and pair them with the exactly
compatible `api.KeySpec`.

```python
from rdp import api

cipher = api.CipherSpec.vigenere(alphabet_size=29)
key_space = api.KeySpec.repeating(length=6)
```

V1 typed constructors cover Vigenere, autokey, columnar, Rail Fence,
substitution, periodic substitution, periodic columnar and the scheduled-stream
families. Their dimensions belong to the specs and are validated before engine
materialisation.

Known-key operations receive semantic tuple values:

```python
rail = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=10)
key: api.ConcreteKey = (7,)
ciphertext = api.encrypt((0, 1, 2, 3), cipher=rail, key=key)
plaintext = api.decrypt(ciphertext, cipher=rail, key=key)
```

The value `(7,)` means seven rails; it is not a legacy offset. Lists and NumPy
arrays must be normalized before crossing the public boundary.

Contributor implementations remain in the exact owning cipher and key-operation
modules. A custom typed two-input map uses
`api.experimental.define_cipher_map`; there is no public runtime cipher object.
