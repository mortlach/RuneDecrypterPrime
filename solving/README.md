# Solving examples

`solving/` contains worked Liber Primus material.

If this is your first time using the bundled Liber Primus material, start with
the [short LP route](getting_started/README.md). It loads a named source,
prepares the reviewed Welcome Pilgrim search, and shows how to run it.

The examples are evidence, not all the same kind of evidence.

The distinction is what information the program receives before the result is
chosen.

## Solved LP workbook

`solved_lp/` contains the solved-page workbook.

Its examples fall into three classes:

**Deterministic replay**  
A known recipe or known key/parameter set is applied to the source. It checks
the source boundary, transform and rendering. It does not demonstrate key
recovery.

**Independent recovery checked afterwards**  
The solver searches without receiving the known key or plaintext. Known truth is
used only after the run to measure recovery.

**Reference-guided reconstruction or diagnostic**  
Known plaintext or other answer-derived information participates in candidate
generation, ranking or selection. This is diagnostic work, not independent recovery.

See [Solved LP workbook](solved_lp/README.md) for the classification of each
file.

## Attempts

`attempts/` is for reproducible work on unsolved or diagnostic material.

An attempt should say what hypothesis is being tested, what source is used, what
prior information is allowed and what outcome would be informative.

See [LP attempts](attempts/README.md).

## Why the evidence label matters

A replay can prove that RDP represents a known solution correctly.

A solver recovery can show that a search method reaches the known answer from a
stated amount of prior information.

A reference-guided reconstruction can test structure around a known answer.

They support different claims.

The same distinction is used in
[Project aims and design principles](../docs/project_overview.md) and
[Comparing solve experiments](../docs/guides/working_a_solve.md).
