# Migration notes — v0.8

This slice adds one real archive pack and one small p13 reference-context pack.

## What this adds

1. the older `no_wli_planning_refactor_20260404` pack is folded under
   `archive/`
2. the p13 real-ciphertext project gets a small upstream p13-readiness context
   pack built from no-WLI / research files that actually mention p13
3. the p13 project gets a note explaining why these files are context rather
   than direct `5455` thread history

## Why this slice matters

It keeps two distinctions clear:
- older no-WLI planning-refactor structure belongs in archive, not in the live
  layer here
- broader p13-readiness thinking can help the real-ciphertext campaign, but it
  is not the same thing as a dedicated old `5455` planning pack
