# Contributing

The easiest way to contribute to RDP is to use it.

Try something against Liber Primus. Change an example. Test a cipher idea. If
you find a bug, tell us. If an explanation is confusing, improve it. If a small
script tests something worth remembering, share it.

You do not need to understand RDP's internals before any of that is useful.

Good places to start:

- [Learn RDP by solving](docs/learn/README.md)
- [Start solving Liber Primus](solving/lp_getting_started/README.md)
- [Liber Primus attempts](solving/attempts/README.md)
- [Uncovering Cicada Wiki](https://uncovering-cicada.fandom.com/wiki/Uncovering_Cicada_Wiki) for wider Cicada 3301 background and current community links

The wiki is also the better long-lived place to find the wider solving community
as Discord servers and invite links change over time.

## Bugs and feature requests

Use [GitHub Issues](https://github.com/mortlach/RuneDecrypterPrime/issues) for
bugs and concrete feature requests.

For a bug, the most useful things are usually what you did, what happened and
what you expected. A small example and the Python/platform details help when they
matter.

For a feature request, start with what you are trying to do. We can work out the
right API afterwards.

## Sharing an LP attempt

A contribution does not need to be a change to RDP itself.

If you tested a real method against Liber Primus, the useful part is often the
experiment:

```text
input
script
what you tried
what happened
```

For attempts kept in the repository, keep the exact input file the script used.
That makes the result much easier to understand later.

See [Liber Primus attempts](solving/attempts/README.md) for the deliberately
lightweight format.

If Git is not your thing, open an issue or share the work with the wider Cicada
community first. Somebody can help turn a useful experiment into a repository
entry later.

## Cipher and method ideas

A new cipher idea can start as a tiny script.

Give it a concrete target. Try it on one LP input. If you are not sure whether
the machinery works, try it on solved material where you can check the answer.
Then change the idea and see what moves.

Some ideas will stay as interesting attempts. Some will grow into methods worth
developing. A few may eventually become reusable RDP ciphers, solvers or scoring
tools.

There is no need to decide which one you have before you start.

## When an experiment grows up

The more formal-looking development material in RDP came from working through a
few genuinely awkward cipher/search problems and finding out what helped.

My own pattern was roughly:

1. get a concrete idea running quickly;
2. check it on something where the answer is known when possible;
3. once a recipe works, keep the important input and settings stable;
4. change things deliberately and watch whether the result moves;
5. when a result becomes important, preserve enough of the recipe that future
   code changes cannot quietly turn it into a different experiment.

The Kaeding, periodic-columnar and overlapping two-period work are examples of
why that became useful. Long searches and complicated pipelines are very easy to
"improve" until you can no longer tell whether you improved the method or simply
changed the experiment. Keeping a known working case around turns drift into a
signal: something changed, so it is worth finding out what.

Broader qualification came later, when I wanted to know whether a result was
robust beyond one prepared example.

These are lessons from developing RDP rather than a checklist you need before
trying a cipher. If the community starts using RDP in different ways, I expect
the useful conventions and examples to evolve too.

For the deeper development path, see
[Cipher development](docs/development/cipher_development.md).

## Contributing code to RDP

RDP has one public Python entry point:

```python
from rdp import api
```

Public examples and callers should stay on that surface.

Inside the implementation, behaviour normally belongs with the cipher, key,
solver, scoring, data or reporting code that owns it. For a small fix, a pull
request is fine. For a larger behavioural or public-API change, opening an issue
first can save a lot of work in the wrong direction.

The reasoning behind the project structure is described in
[Project aims and design principles](docs/project_overview.md) and
[Extending RDP](docs/guides/extending_rdp.md).

A few engineering rules matter once you are changing maintained behaviour:

- Prefer extending or repairing the existing owner of a behaviour rather than
  creating a parallel route around it.
- Avoid silent fallbacks that make it difficult to tell what actually ran.
- Preserve reproducibility where randomness matters.
- Keep known answers out of production ranking, stopping and candidate selection
  unless the method intentionally uses that information.
- Change focused tests and relevant documentation with maintained code.
- Keep generated output, logs and downloaded assets outside the maintained
  source tree.

Some retained development fixtures have extra local checks because they were
frozen after the development work had stabilised. If you change one of those,
follow the README beside it. Those checks are there to make drift visible in
that particular line of work.

## Where to go next

For solving and experiments:

- [Learn RDP by solving](docs/learn/README.md)
- [Start solving Liber Primus](solving/lp_getting_started/README.md)
- [Liber Primus attempts](solving/attempts/README.md)
- [Solved LP workbook](solving/solved_lp/README.md)

For project structure and extension work:

- [Project overview](docs/project_overview.md)
- [Extending RDP](docs/guides/extending_rdp.md)
- [Cipher development](docs/development/cipher_development.md)
- [Development map](docs/development/README.md)

For implementation details:

- [Add a cipher](docs/howto/add_cipher.md)
- [Add a solver](docs/howto/add_solver.md)
- [Build key operations](docs/howto/build_keyops.md)
- [Tests](tests/README.md)
- [Repository tools](tools/README.md)
- [Robustness campaigns](tools/robustness/README.md)
