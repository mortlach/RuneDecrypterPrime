# Cipher implementations

Cipher implementations transform rune indices for a concrete key.

They do not own candidate generation or search.

Candidate-key behaviour belongs to key operations. Search belongs to solvers.
Scoring belongs to the scorer.

The runtime registry maps canonical cipher identities to implementation classes.
The typed public `CipherSpec` binding is separate and includes key compatibility,
validation and materialisation.

See [Cipher runtime and registration](../../../docs/architecture/cipher_runtime_and_registration.md)
and [Add a cipher](../../../docs/howto/add_cipher.md).
