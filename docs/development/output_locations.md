# Output locations

RDP uses one output policy for logging, installation, validation, tutorials and
solved-workbook evidence. `LoggingConfig.output_root` remains the public override.

The first configured destination wins:

1. An explicit output path. Relative library paths resolve from the current directory.
2. `RDP_OUTPUT_ROOT`, which must be a nonempty absolute path.
3. `output/` inside the RDP source checkout containing the installed code.
4. For a package installed without source, the operating system's per-user
   `RuneDecrypterPrime` data directory, with an `output/` child.

Source detection checks RDP's project name and source layout. It works with
source archives and Git worktrees and does not use the terminal's current
folder. The installed-package default uses platformdirs: local application data
on Windows and the XDG user data location on Linux. An unwritable configured
location fails; RDP does not silently choose a different destination.

## Source users

Run the documented installer and examples normally. Generated files go under
the checkout's ignored `output/` directory. Repeated runs receive separate
folders. An explicit `LoggingConfig.run_directory` still selects an exact folder.

## Developers and multiple projects

Keep checkout, interpreter and output choices together in an external launcher.
Resolve its paths from the launcher's own location, then set `RDP_OUTPUT_ROOT`
to an absolute project output directory. For example, a workspace may contain:

```text
workspace/
  checkouts/candidate-a/
  checkouts/candidate-b/
  environments/candidate-a/
  run_outputs/project-a/
  run_outputs/project-b/
  local_archive/
```

Each validation run has a unique directory. Each job inherits its own artifacts
root, so child processes write directly to the correct project. A child's
explicit output override takes precedence. No output-directory discovery,
post-run moves or automatic cleanup is needed. Full assets remain installation
inputs in their existing asset directories.

Metadata keeps the existing portable paths and identity redaction defaults.
Git ignore prevents accidental ordinary additions, but is not an anonymity
filter: raw process output and tracebacks can contain machine paths. Review raw
logs before sharing them. Keep private developer notes under the external output
root as well.
