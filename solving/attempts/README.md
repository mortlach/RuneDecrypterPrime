# Liber Primus attempts

This folder is for concrete things people have actually tried against Liber
Primus.

The easiest place to start is just to pick a target and try something. For
example:

- run Vigenere at a particular period against one LP input;
- change one assumption in an existing example;
- try a transposition or interruptor idea;
- write a small script for a cipher construction you want to explore.

You do not need a grand theory before you start. A useful first experiment can
be a short script and a clear question.

If you want to keep or share the attempt, put the exact input file beside it.
That is the one bit that is very hard to reconstruct reliably later.

A small repository attempt can be as simple as:

```text
solving/attempts/<short-name>/
    README.md
    input.txt
    attempt.py
```

The script and README can both be short.

## Keep the input you actually used

`input.txt` should be the input the experiment really consumed.

If it came from RDP's Liber Primus catalogue, record the source label or locator
too. The catalogue reference tells us where the material came from; the saved
file tells us exactly what this particular script saw.

Plain UTF-8 text is convenient when that matches the experiment. If the script
really consumes another format, keep that file instead and name it clearly.

## A good small attempt can be tiny

For example, a note beside a period-10 Vigenere script could be this small:

```text
Period-10 Vigenere on input.txt.
The period is fixed at 10; attempt.py contains the search I ran.
Nothing convincing came back, but this is the exact input and script I used.
Run: python attempt.py
```

That is already enough for somebody else to pick it up. If you used a crib,
prepared key, unusual scoring or a much larger search, mention that too because
it changes what was really tested.

## Negative results are still results

"Nothing convincing appeared in this search" is useful when the search itself is
clear.

It does not mean the whole cipher family is dead. It means this input, this
method and this amount of search did not produce something useful. Somebody else
can extend it, change one assumption, or avoid unknowingly repeating the same
test.

That is a big part of why this folder exists.

## If the idea starts getting serious

Some attempts stay small. Others turn into a real line of attack.

That is where a bit more experimental discipline starts paying for itself. While
developing RDP, I found it useful to get a method working on material where the
answer could be checked, then keep enough of the successful setup fixed that a
later change in the result was visible rather than mysterious.

The more complicated RDP work — including the Kaeding, periodic-columnar and
overlapping two-period investigations — is where those habits became useful.
Seeds, search budgets, known benchmarks and eventually pinned fixtures were ways
to keep a working result from quietly drifting while the implementation changed.

You probably do not need any of that for the first script. It becomes useful
when you are comparing versions of a method, making stronger claims, or trying
to turn an experiment into something other people can rely on.

For that deeper path, see
[Cipher development](../../docs/development/cipher_development.md).

## Solved material is useful for checking your machinery

If you are not sure whether a new script or search route works at all, try the
same idea on solved material first. It is often much quicker to discover that a
search cannot recover a known answer than to stare at an unsolved result and
wonder whether the cipher idea or the code is the problem.

See [Solved LP workbook](../solved_lp/README.md).

## Share it

If you are comfortable with GitHub, a pull request can add an attempt under this
folder.

If you are not, Git is not a prerequisite for taking part. You can open a
[GitHub Issue](https://github.com/mortlach/RuneDecrypterPrime/issues) with the
input, script and a short description, or share it with the wider Cicada
community.

For background, community resources and current discussion links, start with the
[Uncovering Cicada Wiki](https://uncovering-cicada.fandom.com/wiki/Uncovering_Cicada_Wiki).
