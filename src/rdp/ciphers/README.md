# Cipher implementations

A cipher transforms rune indices according to a rule and a concrete key. Candidate generation belongs to key operations; search strategy belongs to solvers. Start with the implementation closest to the rule you want to investigate.

## Where to look

- [vigenere_cipher.py](vigenere_cipher.py) — Repeating additive transformation.
- [substitution_cipher.py](substitution_cipher.py) — Monoalphabetic substitution.
- [columnar_transposition_cipher.py](columnar_transposition_cipher.py) — Column-order transposition.
- [railfence_cipher.py](railfence_cipher.py) — Rail-fence transposition.
- [autokey_cipher.py](autokey_cipher.py) — Autokey transformation.
- [periodic_substitution_cipher.py](periodic_substitution_cipher.py) — A repeating family of substitution alphabets.
- [periodic_columnar_cipher.py](periodic_columnar_cipher.py) — Periodic substitution with columnar structure.
- [scheduled_stream_lookup_cipher.py](scheduled_stream_lookup_cipher.py) — Scheduled stream transformations.
- [generic_map_cipher.py](generic_map_cipher.py) — Runtime for configured maps and lookups.
- [ciphers_pipeline.py](ciphers_pipeline.py) — Shared permutation, interruptor and transposition processing.
- [interruptors.py](interruptors.py) — Remove and reinsert positions left unchanged.
- [cipher_runtime_registry.py](cipher_runtime_registry.py) — Runtime implementation registration.

## Choices and extension

Choose the family through `api.CipherSpec`. For transpositions, column or rail constraints describe the permitted structure. For stream problems, the supplied schedule and the unknown key play different roles. Interruptor settings describe which positions bypass the normal transformation.

To add a cipher, specify its key layout and compatible key operations, then implement and register its runtime behaviour. Reuse the shared pipeline so position handling stays consistent.

Continue with the [guide](../../../docs/howto/add_cipher.md) or the [package map](../README.md).
