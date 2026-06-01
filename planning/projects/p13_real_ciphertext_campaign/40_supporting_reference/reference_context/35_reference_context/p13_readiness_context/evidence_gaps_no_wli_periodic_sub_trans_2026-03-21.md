# Evidence Gaps And What Would Close Them

Date: 2026-03-21
Status: Working decision memo
Scope: `tools/benchmarks/periodic_sub_trans/no_wli`

## Purpose

This memo separates what is strongly evidenced from what is still partly inferential, and states what further evidence would actually change confidence.

The aim is to stop the programme from speaking with one level of confidence across regimes that do not currently have the same evidence depth.

## Executive Judgement

The project currently has a strong evidence base for one thing:
real, informative hard-family partials on `p9/c3/l1000`, plus a credible diagnosis of the main current blocker.

It does not yet have equally strong evidence for:

- the true scaling boundary
- reliable higher-period behaviour
- the exact role stronger priors will play at short lengths

That does not make the current conclusions weak.
It means the confidence is uneven across regimes, and the programme should say so plainly.

## Strongly Evidenced

### 1. The project can reach informative basins on the hard anchor

This is supported by the best observed `~0.773` behaviour on `p9/c3/l1000`.
That is strong enough to rule out the idea that the solver only produces noise.

### 2. The main current blocker is Stage-3 basin quality

The reports and active plan state clearly that Stage-2 quality stays roughly flat while Stage-3 top-k quality drops sharply in the compared runs.
That is strong evidence that the main regression is inside Stage-3 basin generation rather than everywhere at once.

### 3. The Stage-3.5 proof attempt was invalid as a proof

This matters because it is not merely a disappointing result.
It is a methodology issue.
The requested stage did not actually run in the final artefact.

### 4. Current scorers are imperfect but not obviously the main collapse driver

The reports say the hard family is not globally inverted and that scorer and selector weakness is probably not the dominant explanation of the current regression.

## Partly Evidenced

### 1. Stronger long-context judges will likely help

This is well motivated, and the reports make a persuasive case for it.
But it has not yet been demonstrated directly in the current internal evidence pack on the target tiers.

### 2. Population-level search will likely be needed for higher periods

This is plausible and well argued.
But the current evidence supports it mainly by inference from present limits plus outside method families, not by direct internal success on `p11` to `p13`.

### 3. `p13/l1000` may be feasible with improved basin generation plus stronger late arbitration

This is a plausible mid-term judgement, but it is not yet strongly backed by direct internal evidence.

## Weakly Evidenced Or Still Speculative

### 1. Exact readiness for `p13` to `p14` at `l500`

Direct empirical evidence here is still limited.
The current pack is centred on `p9/c3/l1000`, with thinner coverage at the real short-text high-period edge.

### 2. Exact location of the regime-change boundary

The reports give a sound structural explanation of why difficulty rises with `L/p`, but the precise boundary between mainly search-limited and mainly identifiability-limited behaviour is still partly inferential.

### 3. End-to-end scorer calibration with full heavy assets

The no-bloat snapshot likely excludes some larger LM or scorer assets or calibration artefacts, so end-to-end evaluation of stronger judge ideas is still incomplete.

## What Evidence Would Close The Gaps

### Gap A - True short-text usefulness is not first-class yet

What would close it:

- a benchmark metric set that includes readable chunk counts
- chunk coverage
- region stability across seeds
- a traceable human-happy acceptance path

### Gap B - Higher-period behaviour is thin

What would close it:

- a bridge ladder, not a leap
- controls at `p5` and `p7`
- `p9/c1` as a medium control
- `p9/c3` as the hard anchor
- tracked diagnostics at `p11/l1000`, `p9/l500`, and later `p13/l1000`

That would let the programme identify whether progress generalises before making short-text high-period claims.

### Gap C - Stronger late judges are still mostly argued, not shown

What would close it:

- a controlled late-only reranking study on fixed top-k candidate sets
- comparison between the current judge path and at least one stronger higher-order or LM-based path
- truth-based chunk and rank-regret metrics

### Gap D - Stronger search-family claims are still mostly inferential

What would close it:

- one disciplined prototype family at a time
- better structured moves first
- then one temperature-based multi-chain method
- all tested on the bridge ladder before any `p13/l500` claims

## What Should Not Be Over-Claimed

The programme should not currently claim:

- that `p13/l1000` is near solved
- that `p13/l500` is close
- that current scorers are already adequate for the final goals
- that one strong `p9` family proves general success

## Bottom Line

The evidence base is strong enough to justify the programme continuing and refining its strategy.
It is not yet strong enough to support bold claims about the final short-text high-period regime.

The right next evidence-building steps are:

- bridge-ladder expansion
- partial-solve metrics
- controlled tests of stronger late judges
- controlled tests of stronger search primitives
