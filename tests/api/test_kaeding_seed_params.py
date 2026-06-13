from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases


def test_kaeding_alias_resolver_accepts_seed_selection_params():
    out = resolve_optimizer_aliases(
        "kaeding",
        {
            "steps": 10,
            "seed_selection_metric": "pct",
            "seed_restarts": 3,
        },
    )
    assert out["steps"] == 10
    assert out["seed_selection_metric"] == "pct"
    assert out["seed_restarts"] == 3
