# Language-model runtime

This directory owns the n-gram table runtime used by the normal RDP scorer.

It loads character and WLI model tables, model indices and calibration data.
The native loader accelerates table access. Direction, n-gram order, smoothing
and objective are supplied through the scoring configuration above this layer.

Missing required model assets are errors rather than invitations to select
different evidence.

See [Scoring and language models](../../../../docs/architecture/scoring_and_language_models.md)
and [Installation](../../../../docs/setup/installation.md).
