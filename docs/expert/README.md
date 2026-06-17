# Expert and integrator documentation

Status: expert user guide

This folder is for expert users, external reviewers, and GUI/front-end
integrators.

It explains stable interfaces and design intent. It is not the beginner path,
and it is not the release-contract evidence folder used by tests.

## Read in this order

1. Design goals: [`design_philosophy.md`](design_philosophy.md)
2. Component model: [`component_model.md`](component_model.md)
3. GUI/front-end interfaces: [`gui_frontend_interfaces.md`](gui_frontend_interfaces.md)
4. GUI interface contract: [`gui_interface_contract.md`](gui_interface_contract.md)
5. Stability surface: [`stability_surface.md`](stability_surface.md)

## Core design rule

```text
Friendly at the edge.
Strict in the core.
Visible in reports.
Proved by tutorials and tests.
```

## Important distinction

```text
docs/expert/                  expert-facing explanations and integration guidance
docs/release_contracts/v1/    test-backed contract evidence and drift locks
```

Both are useful, but they serve different purposes.
