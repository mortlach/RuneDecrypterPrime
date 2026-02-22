# Philosophy & Design Principles

Audience: Hands-on / Expert
Time: 5 minutes
Outcome: Understand the project's non-negotiables and why they help
Prereqs: None

> Tracks: Hands-on notes explain what these rules mean for day-to-day tutorials; Expert notes highlight the contracts to keep when extending the system.

## Mission in Plain Language (Hands-on)
- Determinism - keep `seed` fixed so your run matches everyone else's.
- Transparency - enums (Direction, Device, Solver) are visible on the surface; telemetry shows what happened.
- Single path - tutorials follow the same RunAPI -> Solver -> Telemetry pipeline, so debugging and sharing are simple.

## Contract for Contributors (Expert)
1. Deterministic by default - every solver, helper, and tutorial must take an explicit seed. Guarded by `tests/smoke/test_determinism_canary.py`.
2. Two-layer model - API is forgiving (strings accepted), core uses enums/config dataclasses. Guarded by normaliser tests and guardrails.
3. Separation of concerns - API -> Problem -> Engine -> Solver -> Scoring -> Telemetry. Each layer has its own tests.
4. Observability - telemetry schema is minimal but mandatory (`telemetry.run`, `solver_progress`, `solution.meta["work"]`). Turning it off is explicit.
5. Teachability first - tutorials are workflow-agnostic and reproducible; canonical names only, no deprecated alias chatter.

## How To Use These Principles
### Hands-on
- Start from tutorials; match seeds and log folders before experimenting.
- When stuck, see `docs/guides/troubleshooting.md` mapped to the determinism + telemetry pillars.

### Expert
- Before merging, confirm: seed path intact, telemetry fields present, outputs still under `output/`.
- Reference `docs/DOCS_PLAN.md` and `docs/DOCS_PLAN_IMPLEMENTATION.md` when editing guides or adding components.

## FAQ
- Which workflow is preferred? Any workflow is valid if runs remain deterministic and telemetry-complete.
- Can I change default seeds? Yes, but document the reason and update telemetry contract tests.
- What if I need silence in logs? Disable `print_progress`, not telemetry; telemetry stays on so results remain auditable.

## Related Docs
- `guides/architecture.md` - overview of how the layers connect.
- `guides/documentation_playbook.md` - writing standards derived from these principles.
- `README.md` - restates mission/guardrails for new contributors.

