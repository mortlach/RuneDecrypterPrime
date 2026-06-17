# Expert and integrator documentation

Status: expert user guide

This folder is for expert users, external reviewers, and GUI/front-end
integrators.

It explains stable interfaces and design intent. It is not a place for old
implementation diaries or local evidence bundles.

## Read in this order

1. Design goals: [`design_philosophy.md`](design_philosophy.md)
2. Component model: [`component_model.md`](component_model.md)
3. Contracts overview: [`contracts_overview.md`](contracts_overview.md)
4. GUI/front-end interfaces: [`gui_frontend_interfaces.md`](gui_frontend_interfaces.md)
5. GUI interface contract: [`gui_interface_contract.md`](gui_interface_contract.md)
6. Stability surface: [`stability_surface.md`](stability_surface.md)
7. Reports and artefacts: [`reports_and_artifacts.md`](reports_and_artifacts.md)
8. Source and tutorial interfaces: [`source_and_tutorial_interfaces.md`](source_and_tutorial_interfaces.md)
9. Plugin design: [`plugin_design.md`](plugin_design.md)

## The core design rule

```text
Friendly at the edge.
Strict in the core.
Visible in reports.
Proved by tutorials and tests.
```

## Stable user-facing surfaces

The most important surfaces for expert users and GUI/front-end developers are:

```text
tutorials/v1/tutorial_manifest_v1.json
tutorials/v1/run_all.py
docs/guides/tutorial_catalogue.md
docs/guides/common_run_options.md
output/tutorials/
structured reports and telemetry under output/
```

Python API surfaces are useful for integrators, but a GUI should avoid scraping
human console output as its main interface.
