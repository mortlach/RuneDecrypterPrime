# Migration notes — v0.18

This slice does two things:

1. it strengthens `p13_real_ciphertext_campaign` by defining the first actual
   comparison/control attempt without inventing a fake result
2. it adds a bundle-wide cutover-status assessment against the canonical
   cutover criteria

## Why this slice matters

The p13 real-ciphertext home had a pinned control package, but not yet a first
actual attempt definition.

The bundle as a whole also needed a more honest answer to:
- how close are we to treating this as canonical day-to-day planning?

This slice addresses both.
