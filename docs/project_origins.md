# Project origins

RDP has a longer history than the current Python codebase.

The earliest experiments date to around 2014 and were developed in Mathematica
while the underlying way of describing the cipher problem was still taking
shape. A later C++ generation moved the work toward something portable enough
to share with other solvers rather than keeping the experiments tied to one
environment.

Python came later. Community pressure for something easier to use and extend was
a fairly effective incentive to learn it. The application, language-model
tooling and associated solving workflows then went through several substantial
generations before reaching the present V1 structure.

The exact generation count depends on where the boundaries are drawn. Three
major versions of the application and language-model work is a conservative
description. Counting the intermediate redesigns gives something closer to
five. The conceptual model underneath them evolved in the same way: cipher
hypothesis, key structure, search, scoring evidence and evaluation became more
explicit with each generation.

The current project is therefore not a direct translation of the early code.
What survived is the method: make the assumptions visible, keep the parts of the
problem separable, and make it possible to compare one experiment with another.

For the present design, see
[Project aims and design principles](project_overview.md).

For the public extension model, see [Extending RDP](guides/extending_rdp.md).
