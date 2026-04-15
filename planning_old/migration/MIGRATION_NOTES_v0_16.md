# Migration notes — v0.16

This slice tightens `rdp_v1` in the same way the previous slice tightened the
benchmark scoring/Torch layer.

## What this adds

1. a detailed `rdp_v1` support-layer freshness crosscheck
2. a recommended keep-set / archive-later split for `rdp_v1` support files
3. a project-level cut-over checklist for `rdp_v1`
4. a small global canonical-cutover criteria note

## Why this slice matters

The main remaining active-home uncertainty is now:
- which `rdp_v1` support notes should remain live support
- which are better treated as historical support
- what the minimum cut-over bar should be before calling the bundle canonical

This slice makes that explicit.
