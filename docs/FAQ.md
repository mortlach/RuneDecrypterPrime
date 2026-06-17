# FAQ

## What is RDP?

Rune Decrypter Prime is a deterministic toolkit for running and checking
29-rune decryption experiments.

## What should I run first?

From the repository root:

```text
python install.py
python tutorials/v1/run_all.py
```

## How do I know it worked?

The tutorial runner should end with:

```text
failed   : 0
```

Some tutorials are exact solves. Some are accepted near-solves. The tutorial
summary and manifest define the expected result.

## Where are the results?

Generated output is written under:

```text
output/
```

Tutorial output is usually under:

```text
output/tutorials/
```

For more detail, read:

```text
docs/guides/outputs.md
docs/expert/reports_and_artifacts.md
```

## What should I read after the quickstart?

Read:

```text
docs/guides/first_real_solve.md
docs/guides/using_rdp.md
docs/guides/examples.md
```

## I am an expert user. Where are the deeper docs?

Start here:

```text
docs/expert/README.md
```

Then read:

```text
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

## I am building a GUI or overlay. What should I read?

Read:

```text
docs/expert/gui_frontend_interfaces.md
docs/expert/gui_interface_contract.md
docs/expert/reports_and_artifacts.md
docs/expert/source_and_tutorial_interfaces.md
```

The short version is:

```text
Use tutorial manifests and run specs as the input surface.
Use output reports, artefacts, and telemetry as the display surface.
Do not scrape human console text as the main interface.
```

## What if a tutorial fails?

Start with:

```text
docs/guides/troubleshooting.md
```

The most common causes are:

```text
wrong Python environment
wrong working directory
missing package install
asset profile mismatch
tutorial gate mismatch
stale output from an older run
```

## What are Liber Primus labels?

They are user-facing names for known Liber Primus source fragments.

Read:

```text
docs/guides/liber_primus_solved_sources.md
docs/expert/source_and_tutorial_interfaces.md
```

## Is every experiment in the repo part of V1?

No.

The user docs are for the normal V1 surface. Experimental research and old
implementation-history material are not part of the normal user path.
