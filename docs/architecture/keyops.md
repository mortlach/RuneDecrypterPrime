# KeyOps

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Understand verbs and invariants for keys
Prereqs: None

**Concept**  
Operations that create and change keys during search, with invariants enforced per key type.

## Verbs
- `random()` - new random key  
- `mutate(key)` - small change (local move)  
- `neighbour(key)` - minimal local change  
- `recombine(k1, k2)` - crossover for GA  
- `make_population(base, size)` - initialise a pool  
- `normalize(key)` - enforce KNF if needed

## Invariants
- **Permutation keys**: always a bijection (length 29 or N).  
- **Vector keys**: values are mod-29; length preserved.

## RNG discipline
All randomness is injected by the Engine (named child streams). No global RNG calls in KeyOps.

**Example (shape)**
```python
# Inside an optimiser step (shape only)
k = keyops.random()
k2 = keyops.mutate(k)
k3 = keyops.recombine(k, k2)
k3 = keyops.normalize(k3)
```

**See also**  
[Ciphers](ciphers.md) · [Optimisers](optimisers.md)

[<- Ciphers](ciphers.md) · [Next -> Optimisers](optimisers.md)

**Related tests**
- `tests/keyops/test_permutation_key_ops.py`
- `tests/keyops/test_vector_key_ops.py`
