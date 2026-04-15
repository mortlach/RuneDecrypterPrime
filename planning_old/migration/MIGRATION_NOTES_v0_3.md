# Migration notes — v0.3

This slice adds the first real status/log artefact for the `5455` thread and the
first controlled move of old material into `completed/` and `legacy/`.

## What this adds

1. `p13_real_ciphertext_campaign`
   - first compact `5455` status ledger
   - first result/status log note

2. `completed/lp_domain`
   - first completed-capability home
   - promoted old LP domain planning docs

3. `legacy/v1_old_active_index`
   - first legacy home for the old active-index residue
   - preserves context without letting the old files keep acting as live truth

## Why this matters

Up to v0.2 the new framework mostly created homes and maps.
v0.3 starts doing two more important things:
- it creates a real update surface for a named problem thread
- it begins pushing old planning down into safer non-live homes
