# Benchmarking TODO

When 2-grams help (in your exact situation)

After some substitution has been peeled off (even partially).
Then bigrams start to carry real language signal and can help pick the right basin faster.

For product-cipher confirmation (ranking columns/orders once you're "close-ish").
Bigrams can be more discriminating than unigrams without being as brittle as 3/4-grams.

When 2-grams don't help (or hurts)
On raw ciphertext before any substitution layer is handled: bigram evidence is mostly destroyed, so you get spiky noise and false winners.

Keep it minimal and decisive:

Don't replace char1. Add a third profile:

A_char1 (robust scout)

M_char12 (char1+char2, e.g. weights {1:0.4, 2:0.6})

B_char34 (confirm)

Use char2 only in rerank / promote steps, not in the raw column scan:

Pass A: column shortlist with char1

Pass B: rerank top K columns with char12

Deepen: char34

Measure success by time-to-stable-uplift, not best score:

Does char12 reach the same "best candidate key" with fewer chunks / evals?

Does it reduce seed-to-seed variance?
