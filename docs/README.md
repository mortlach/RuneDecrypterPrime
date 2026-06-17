# Rune Decrypter Prime documentation

This is the user documentation for Rune Decrypter Prime.

It has two levels:

```text
beginner path       install, run, inspect, repeat
expert path         understand contracts, interfaces, components, plugins
```

## New user path

1. Install: [`setup/installation.md`](setup/installation.md)
2. Run tutorials: [`guides/quickstart.md`](guides/quickstart.md)
3. Read one complete solve: [`guides/first_real_solve.md`](guides/first_real_solve.md)
4. Learn normal use: [`guides/using_rdp.md`](guides/using_rdp.md)
5. Fix common problems: [`guides/troubleshooting.md`](guides/troubleshooting.md)

## Beginner-friendly guides

```text
guides/quickstart.md
guides/first_real_solve.md
guides/using_rdp.md
guides/features.md
guides/common_run_options.md
guides/tutorial_catalogue.md
guides/examples.md
guides/outputs.md
guides/troubleshooting.md
guides/liber_primus_solved_sources.md
```

## Expert and integrator path

Use this path if you are an expert client, advanced user, reviewer, or someone
building a GUI/front-end on top of RDP:

```text
expert/README.md
expert/design_philosophy.md
expert/component_model.md
expert/contracts_overview.md
expert/gui_frontend_interfaces.md
expert/gui_interface_contract.md
expert/stability_surface.md
expert/plugin_design.md
expert/reports_and_artifacts.md
expert/source_and_tutorial_interfaces.md
```

These docs explain stable interfaces and design intent without exposing old
implementation-history material.

## Tutorials

Tutorial notes are under:

```text
tutorials/
```

Runnable tutorial scripts are under:

```text
../tutorials/v1/
```

The tutorial runner is:

```text
../tutorials/v1/run_all.py
```

The tutorial manifest is:

```text
../tutorials/v1/tutorial_manifest_v1.json
```

## Reference for users

```text
FAQ.md
glossary.md
```

## Generated output

RDP writes generated logs and reports under:

```text
../output/
```

Do not commit generated output.
