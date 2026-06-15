# D7 tutorial benchmark match-ratio addendum

Superseded by the source contract in `rune_decrypter_prime.utils.tutorial_benchmark` and its tests.

Current D7 rule:

- Tutorial reference policies may be declared before all comparison inputs are attached.
- When comparison inputs are present, the summary reports `match_ratio`, `readable_reached`, and `target_reached`.
- `TutorialTruthPolicy.NONE` must not report a match ratio.
- If `match_ratio` is present, the readable and target fields must also be present.
