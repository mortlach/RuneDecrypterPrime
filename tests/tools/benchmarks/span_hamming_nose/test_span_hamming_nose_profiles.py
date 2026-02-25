from __future__ import annotations

import pytest

from tools.benchmarks.config.span_hamming_nose_profiles import (
    get_span_hamming_nose_profile,
)


pytestmark = pytest.mark.tier_a


def test_profile_lookup_default_and_smoke() -> None:
    full = get_span_hamming_nose_profile("span_hamming_nose_v1")
    smoke = get_span_hamming_nose_profile("span_hamming_nose_smoke_v1")

    assert full.profile_id == "span_hamming_nose_v1"
    assert smoke.profile_id == "span_hamming_nose_smoke_v1"
    assert smoke.samples_per_bucket <= full.samples_per_bucket
    assert len(smoke.length_buckets) <= len(full.length_buckets)


def test_profile_lookup_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown span_hamming NOSE profile_id"):
        get_span_hamming_nose_profile("does_not_exist")

