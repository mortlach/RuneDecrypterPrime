# Migration notes — v0.12

This slice makes the remaining work explicit inside the bundle and adds two
small support/reference promotions where the fit is clear.

## What this adds

1. global remaining-work and crosscheck files
2. per-project remaining-work files for the three active homes
3. one small benchmark scoring/reference promotion
4. one small forensic/archive promotion

## Why this slice matters

The bundle is now large enough that it needs to carry its own "what is left"
map.

This slice does that, and also captures a few obvious still-loose files without
doing a blind bulk move.
