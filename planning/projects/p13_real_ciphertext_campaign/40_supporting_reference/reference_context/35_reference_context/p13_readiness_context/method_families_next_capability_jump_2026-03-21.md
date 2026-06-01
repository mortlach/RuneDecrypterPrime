# Method Families Comparison For The Next Capability Jump

Date: 2026-03-21
Status: Working decision memo
Scope: `tools/benchmarks/periodic_sub_trans/no_wli`

## Purpose

This memo compares the main method families that could plausibly move the programme from current `p9` hard-anchor partials toward stronger `p11` to `p13` behaviour.

It is not a literature survey.
It is a practical note on what each family is good for, why it might help here, why it might fail here, and how naturally it fits RDP.

## Executive Judgement

The next capability jump should not be framed as a choice between "keep tuning the current solver forever" and "replace everything with something exotic."

The credible next method families fall into three layers:

1. improve the current structured local-search family
2. improve late discrimination and selection
3. add stronger global exploration once the baseline is stable

The broad reports support that layered view.
They do not support jumping straight to the most speculative methods first.

## Family 1 - Stage-3 basin recovery and stronger structured local moves

This includes:

- restoring the older stronger Stage-3 behaviour
- adding better block-aware moves
- using segment transforms and multi-swaps that respect cipher structure
- improving how candidates are promoted into deep refinement

Why it might help:

- the strongest current evidence says the main regression is inside Stage-3 basin generation
- if the existing solver family is reaching the wrong basins, late logic will not rescue it

Why it might fail:

- this can become a long tail of local knob-tuning
- it may restore lost performance without changing the eventual `p13/l500` ceiling

Fit to RDP:

- very strong

Recommendation:

- this remains the right immediate workstream for solve improvement
- keep it disciplined and hypothesis-driven rather than endless micro-tuning

## Family 2 - Stronger late judges and rerankers

This includes:

- higher-order char or mixed char and word scoring
- compact neural character-LM rerankers
- explicit lexical or keyword-style acceptance gates

Why it might help:

- longer-context evidence matters more as length drops and period rises
- at `l500`, a short-window scorer may not separate the true candidate cleanly enough even if search reaches a useful basin

Why it might fail:

- a stronger reranker can still reward plausible gibberish if the corpus or preprocessing is mismatched
- it can also become a throughput burden if applied too early or too broadly

Fit to RDP:

- strong, especially if kept late-only at first

Recommendation:

- this is the best next extension after the `p9` hard-anchor path is stable
- it is especially promising for short-text partial-solve goals

## Family 3 - Simulated annealing, MH acceptance, and parallel tempering

This family strengthens exploration in rugged landscapes by allowing controlled acceptance of worse states and by maintaining multiple chains at different temperatures.

Why it might help:

- if the higher-period problem is getting trapped in poor local optima, this family addresses that directly
- it extends the current stochastic-search style rather than replacing it

Why it might fail:

- it adds tuning burden and compute cost
- it still depends on the score landscape being informative enough for temperature-based exploration to help

Fit to RDP:

- reasonably strong

Recommendation:

- this is the most serious candidate for the first true search-family upgrade after the current local baseline is stabilised

## Family 4 - Cross-entropy and other population search methods

This family maintains a distribution over promising structured keys or moves and updates it using elites.

Why it might help:

- population methods can explore broader regions of key space more systematically than unrelated restarts
- they may be useful once the solver needs to carry uncertainty over multiple plausible basin families

Why it might fail:

- they are feature-design heavy
- they can collapse prematurely if the representation is poor
- they demand more engineering and stronger determinism discipline

Fit to RDP:

- moderate

Recommendation:

- worth studying, but not the first major search-family addition

## Family 5 - MCTS or UCT on a decomposition

This family treats part of the solve as a tree over partial structural decisions, with rollouts driven by the existing solver.

Why it might help:

- if transposition or route structure can be explored progressively while substitution is handled in rollouts, this could impose better global structure on exploration

Why it might fail:

- branching could explode
- rollouts could be too noisy
- the decomposition might not match the real hard structure well enough

Fit to RDP:

- moderate to weak for now

Recommendation:

- research candidate only, not a near-term engineering priority

## Family 6 - CP-SAT or exact subproblem optimisation

This family uses exact or near-exact optimisation for restricted subproblems, not for the full ciphertext-only solve.

Why it might help:

- for alignment, segment assignment, or restricted route and selection problems, exact optimisation may remove heuristic guesswork

Why it might fail:

- the global problem is unlikely to fit this approach directly at high period
- modelling effort can be high and gains can stay narrow

Fit to RDP:

- moderate for subproblem hooks
- weak as a whole-programme answer

Recommendation:

- keep as a targeted side tool, not a main method family

## Family 7 - Explicit crib, keyword, and chunk gates

This family turns "human would be pleased with this partial" into formal late-stage acceptance signals.

Why it might help:

- the final goal for `p13/l500` is not necessarily exact recovery
- human-useful chunk recovery matters, and this family makes that objective explicit and measurable

Why it might fail:

- it can bias the system toward false positives if used too early or too strongly

Fit to RDP:

- strong as a late-stage audited acceptance layer

Recommendation:

- develop this alongside stronger late judges
- do not treat it as a substitute for search

## Ranked Recommendation

For the next capability jump, the method-family order should be:

1. recover and improve structured local basin generation
2. add stronger late-only judges and chunk-aware acceptance logic
3. add parallel tempering or a closely related exploration upgrade
4. only then consider heavier population methods
5. keep MCTS and CP-SAT as research-side options, not immediate workstreams

## Bottom Line

The most credible path upward is not "invent the most advanced new algorithm first."

It is:

- stabilise and strengthen basin generation
- improve late discrimination with longer-context evidence
- then introduce more powerful global exploration once the current pipeline is giving clear, attributable signals
