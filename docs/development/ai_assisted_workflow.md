# AI-assisted development

AI coding tools have been used in RDP's development workflow. They have also been useful
when working with RDP as a solver.

A modern coding assistant can usually read the public API and documentation,
help turn a cipher idea into a small experiment, explain an unfamiliar example,
write tests, or in some environments run the code and inspect the result.

Use that as much or as little as you find useful.

## What has worked well here

A few habits have made AI-assisted work much more useful during RDP development:

- give the tool the current API and documentation rather than asking it to
  invent an interface
- start with a small experiment that can actually be run
- use solved material or another known case when you need to check that the
  machinery works
- inspect the real inputs and effective settings rather than trusting a
  plausible description of what ran
- keep tests that expose a genuine boundary or regression
- use longer robustness runs only when the question needs more than one good
  example
- review the result as code and evidence, not as an answer that becomes true
  because a model produced it

The tools are especially good at accelerating the mechanical parts of an investigation: wiring an experiment together, comparing variants, reading a large API surface, expanding test coverage and checking documentation against code.

There is a more important thing to beware of. Modern AI tools are extremely good at finding and completing patterns, including patterns that are weak, accidental or simply not there. Given enough suggestive fragments, they can turn noise into a very convincing story. Cipher solving is already vulnerable to this kind of over-interpretation, so AI can make a sloppy solve look much stronger than it is.

Treat explanations, apparent patterns and proposed plaintexts as hypotheses. Run the experiment, keep the exact input and settings, and check the result independently. A persuasive explanation is not evidence that the cipher was solved.

## The standard does not change

Whether an experiment was written by hand, with an AI assistant, or by some mix
of the two, somebody else should be able to inspect the input, code and result
and verify the claim independently.

For a small shared LP attempt that may mean little more than the exact input,
the script and a note about what happened. For a serious cipher-development
result it may also mean fixed settings, seeds, benchmarks or broader robustness
evidence.

The result still has to stand on its own.
