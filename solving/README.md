# Solving examples

`solving/` contains worked Liber Primus material.

If you are still learning the basic RDP run model, start with
[Learn RDP by solving](../docs/learn/README.md).

If you are ready to work with the bundled Liber Primus material, choose the
route that matches what you want to do:

- [Getting started with Liber Primus](getting_started/README.md) is the compact
  code bridge: load a source, prepare the reviewed Welcome Pilgrim search, then
  run it.
- [Start solving Liber Primus](lp_getting_started/README.md) is the gentler
  worked route through real solved material. It leaves the cryptanalytic choices
  visible and builds from small experiments.
- [Solved LP workbook](solved_lp/README.md) contains the detailed replay,
  recovery and diagnostic examples used as evidence.

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
