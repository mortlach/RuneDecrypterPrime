# Project history

Rune Decrypter Prime did not begin with the V1 repository.

I started developing tools, data and techniques for working with the Cicada 3301
runes in 2014. Over the following years that work moved through several solvers,
experiments, public repositories and private development branches before being
brought together into RDP.

Much of that lineage is visible on the
[mortlach GitHub account](https://github.com/mortlach), together with the public
solvers and surviving solving activity around the project. Private repositories
and personal solving logs cover parts of the development that were never public.
The provenance of the underlying work predates modern code-generation tools by
many years.

The implementations have changed repeatedly. The work on rune handling,
language data, ciphers, search methods and Liber Primus did not appear with this
repository.

RDP V1 is an attempt to bring that accumulated work into one package that other
people can install, inspect, test and extend.

## AI-assisted development

Modern AI coding tools became useful enough during 2025 that I began using them
substantially in RDP development.

Used well, they have accelerated the work enormously. In particular they made it
practical to expand implementation, testing, documentation, consistency checks
and robustness work much further than I could have managed at the same pace
alone.

They did not replace the earlier cryptanalytic work or its provenance. They
became another development tool used to implement, review and test it.

The same standard still applies to the result: code, examples and claims should
be independently inspectable and verifiable from the repository, the inputs and
the evidence produced by the run.
