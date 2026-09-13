# Candidate evaluation

The problem runtime binds one cipher, one scorer, the ciphertext/WLI and the
runtime KeyOps.

Solvers evaluate candidate keys through this boundary.

The main path is:

```text
key
-> decrypt
-> constraints
-> score
```

Interruptor search can split a composite key into its core key and interruptor
positions before decryption.

See [Candidate evaluation](../../../../docs/architecture/candidate_evaluation.md).
