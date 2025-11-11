# Solvers - Practical Playbook

Audience: Expert
Time: 6-10 minutes
Outcome: Know when to pick Beam/GA/SA/Hybrid and how progress/telemetry works
Prereqs: Read Architecture overview; ran at least one tutorial

Counters: `step`, `evals`, `since_improve`. Budgets: `eval_budget` or algorithm knobs.

- Beam: breadth-limited frontier; deterministic tie-breaks.
- GA: population -> selection -> recombination -> mutation.
- SA: neighbour moves with a schedule.
- Hybrid: Beam -> GA -> SA; phase telemetry recorded.

Hold `seed` and `scorer` constant when comparing solvers.

