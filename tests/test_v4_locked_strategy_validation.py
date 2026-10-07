from __future__ import annotations

import pandas as pd

from mma_v4.locked_strategy_validation import (
    LOCKED_BENCHMARKS,
    LOCKED_PRIMARY_SELECTOR,
    _locked_selector_log,
)


def test_locked_strategy_constants_are_frozen() -> None:
    assert LOCKED_PRIMARY_SELECTOR == "quarterly__min_bets_50__min_windows_5__default_during_burnin"
    assert LOCKED_BENCHMARKS == [
        "confidence_ge_0.6__shrunk_kelly_s0.5_k0.25_cap_0.5pct",
        "underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct",
        "favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct",
        "edge_ge_0.05__flat_1u",
    ]


def test_locked_selector_log_filters_only_primary_and_marks_scope() -> None:
    raw = pd.DataFrame(
        [
            {
                "selector_config": LOCKED_PRIMARY_SELECTOR,
                "selection_mode": "normal",
                "fight_date": "2024-01-01",
                "test_window_label": "2024Q1",
            },
            {
                "selector_config": LOCKED_PRIMARY_SELECTOR,
                "selection_mode": "burnin_default",
                "fight_date": "2021-01-01",
                "test_window_label": "2021Q1",
            },
            {
                "selector_config": "card__min_bets_50__min_windows_5__default_during_burnin",
                "selection_mode": "normal",
                "fight_date": "2024-01-01",
                "test_window_label": "2024-01-01",
            },
        ]
    )

    out = _locked_selector_log(raw)

    assert len(out) == 2
    assert set(out["result_scope"]) == {"excluding_burnin", "burnin_only"}
    assert set(out["comparison_name"]) == {"locked_quarterly_selector"}
