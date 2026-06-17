# Rune Decrypter Prime

Rune Decrypter Prime (RDP) is a deterministic toolkit for running and checking
29-rune decryption experiments.

The aim is simple:

```text
run a solve
see what happened
compare the result
repeat it later
```

## Start here

1. Install RDP: [`docs/setup/installation.md`](docs/setup/installation.md)
2. Run the tutorials: [`docs/guides/quickstart.md`](docs/guides/quickstart.md)
3. Read one complete solve walkthrough: [`docs/guides/first_real_solve.md`](docs/guides/first_real_solve.md)
4. Learn normal use: [`docs/guides/using_rdp.md`](docs/guides/using_rdp.md)
5. Troubleshoot setup or runs: [`docs/guides/troubleshooting.md`](docs/guides/troubleshooting.md)

## Expert and GUI/front-end docs

For expert users, reviewers, and GUI/front-end integrators:

```text
docs/expert/README.md
docs/expert/design_philosophy.md
docs/expert/component_model.md
docs/expert/contracts_overview.md
docs/expert/gui_frontend_interfaces.md
docs/expert/gui_interface_contract.md
docs/expert/stability_surface.md
docs/expert/plugin_design.md
docs/expert/reports_and_artifacts.md
docs/expert/source_and_tutorial_interfaces.md
```

These explain stable user-facing interfaces, design goals, component boundaries,
plugin ideas, reports, and integration surfaces.

## Quick install

From the repository root:

```text
python install.py
```

On Windows:

```text
install.bat
```

## Quick tutorial run

```text
python tutorials/v1/run_all.py
```

Success means the tutorial summary reports:

```text
failed   : 0
```

## Useful user docs

```text
docs/README.md                         documentation map
docs/FAQ.md                            common questions
docs/glossary.md                       common terms
docs/setup/installation.md             install and first checks
docs/guides/quickstart.md              shortest working path
docs/guides/first_real_solve.md        one full solve explained
docs/guides/using_rdp.md               normal user workflow
docs/guides/features.md                feature overview
docs/guides/common_run_options.md      common choices users can set
docs/guides/tutorial_catalogue.md      tutorials and what they prove
docs/guides/examples.md                beginner examples
docs/guides/outputs.md                 where results are written
docs/guides/troubleshooting.md         common fixes
docs/guides/liber_primus_solved_sources.md  LP source labels
docs/tutorials/                        tutorial notes
docs/expert/                           expert and integration docs
```

The public docs are intended to help users install, run, inspect, repeat, and
integrate RDP solves.
