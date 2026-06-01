# Capability Ladder For No-WLI Periodic Substitution + Transposition

Date: 2026-03-21
Status: Working decision memo
Scope: `tools/benchmarks/periodic_sub_trans/no_wli`

## Purpose

This memo states, in one place, what the programme has actually shown, what looks credibly within reach next, what would count as a real breakthrough, and what remains speculative.

It is intended to stop the team sliding between "good hard-anchor partials" and "nearly ready for `p13/l500`" without a clear capability ladder.

## Executive Judgement

The current no-WLI programme is promising, but it is still in the middle zone between "credible hard-family partial solver" and "reliable general solver."

The strongest current evidence is the real basin-reaching capability on `p9/c3/l1000`, with best observed match around `0.773`.
That is strong enough to count as genuine partial recovery rather than noise.

At the same time, the evidence pack also shows that this capability is not yet stable:

- there has been a Stage-3 basin regression
- a bounded Stage-3.5 proof attempt was invalid because the requested stage did not actually run

So the programme has already crossed one important threshold:
it no longer needs to prove that the problem is tractable at all.

What it has not yet crossed is the next threshold:
reliable, well-attributed behaviour under fixed budgets and across seeds.

## Capability Ladder

### Level 0 - Architecture and methodology viability

Status: achieved

At this level, the question is whether the project has a plausible framework for real cryptanalytic work rather than a one-off script pile.
The answer is yes.

RDP already has a staged pipeline, modular scorer and solver structure, and an audit and trace intent that are directionally good enough to support serious work.

This does not mean the engineering is perfect.
It means the structure is viable.

### Level 1 - Genuine hard-anchor basin reach

Status: achieved, but not yet reliable

This is the current strongest evidence-backed level.
The programme has shown credible partial solutions on the `p9/c3/l1000` hard anchor, with best observed match around `0.773` and repeated strong runs in the `0.76` to `0.77` band in the historical evidence.

That is enough to say the project can reach informative basins, not just produce plausible-looking gibberish.

### Level 2 - Stable and attributable hard-anchor performance

Status: not yet achieved

This is the next real milestone.
It means not merely "one good run existed once," but:

- strong `p9/c3/l1000` partials recur under fixed budgets
- the pipeline stages do what they claim
- the team can distinguish search failure from scorer failure from plumbing drift

The Stage-3 basin regression and the invalid Stage-3.5 proof attempt both show that this level has not yet been secured.

### Level 3 - General `p9` family robustness

Status: partly demonstrated, not yet locked down

This level means the programme is not only good at one anchor.
It should be healthy across:

- easy controls
- medium controls such as `p9/c1`
- the hard anchor `p9/c3`

The reports already point in this direction, but the benchmark and acceptance rules are not yet first-class enough to claim this level cleanly.

### Level 4 - Credible bridge into higher period at `l1000`

Status: not yet achieved

This is where the solver starts showing convincing upward movement on `p11/l1000` and then `p13/l1000`, even if routine full solves are still absent.

The reports are clear that this jump is not incremental.
It likely requires both stronger basin generation and stronger late discrimination than the current short-window stack alone.

### Level 5 - Reliable `p13/l1000` full solve

Status: aspirational, but not unreasonable

This is the first major destination target.
The reports treat it as difficult but plausible if several things improve together:

- Stage-3 basin quality
- stronger late arbitration
- likely some form of population-level exploration rather than single-chain local search alone

This should be treated as a serious mid-term research target, not as something almost already done.

### Level 6 - Reliable `p13/l500` human-useful partial solve

Status: still speculative

This is the real stretch goal.
At `p13` to `p14` and `l500`, the problem becomes much more information-limited:

- samples per phase fall sharply
- longer-context evidence matters more
- identifiability problems become real

The reports also argue that "single-chain hillclimb + short-window n-gram" is unlikely to be reliable here without stronger priors, stronger validators, and more global search.

So this level should not be treated as a near-term engineering target.

## What Would Count As A Real Breakthrough

A real breakthrough is not just "best run improved a bit."

The first real breakthrough would be:

- stable recovery of strong `p9/c3/l1000` basins under fixed budgets and across seeds
- trustworthy stage semantics and clean attribution

The second real breakthrough would be:

- credible upward movement on `p11/l1000` and `p13/l1000`
- plus visible improvement on short-text bridge families like `p9/l500`

The third real breakthrough would be:

- reliable chunk-rich partials on `p13/l500` under fixed budgets and without cherry-picking

## What Remains Speculative

Three areas should still be treated as partly inferential:

- the exact boundary between search-limited and information-limited behaviour at high period and short length
- the real benefit of stronger long-context validators in the current stack
- whether population methods or decomposition methods will outperform better local structured moves in this exact setting

## Bottom Line

The programme has already earned the label `credible hard-family partial solver`, but not yet `reliable general solver`.

The next honest milestone is not "solve `p13/l500`."
It is "stabilise and generalise the current `p9` hard-family capability so that higher-period progress becomes interpretable and believable."
