from __future__ import annotations

import pandas as pd

from mma_v4.rolling_betting import (
    StrategyHistory,
    _empty_log,
    assign_card_metadata,
    breakdown_rows,
    build_windows,
    select_strategy,
)


def _predictions() -> pd.DataFrame:
    rows = []
    for i, date in enumerate(["2021-01-01", "2021-01-08", "2021-02-01", "2021-04-01"]):
        rows.append(
            {
                "fight_id": f"f{i}",
                "fight_date": date,
                "test_year": 2021,
                "fighter_a": f"A{i}",
                "fighter_b": f"B{i}",
                "actual_winner": f"A{i}",
                "market_favorite": f"A{i}",
                "model_pick": f"A{i}",
                "model_confidence": 0.6,
                "pred_prob_a": 0.6,
                "pred_prob_b": 0.4,
                "odds_a": -120,
                "odds_b": 110,
                "implied_prob_a": 0.545,
                "implied_prob_b": 0.476,
                "model_edge_a": 0.055,
                "model_edge_b": -0.076,
                "is_main_card": i % 2 == 0,
                "profit_per_1_a": 0.833,
                "profit_per_1_b": 1.1,
                "decimal_odds_a": 1.833,
                "decimal_odds_b": 2.1,
            }
        )
    return assign_card_metadata(pd.DataFrame(rows))


def _log(strategy: str, cards: list[int], pls: list[float]) -> pd.DataFrame:
    rows = []
    bankroll = 100.0
    peak = 100.0
    dates = ["2021-01-01", "2021-01-08", "2021-02-01", "2021-04-01"]
    for seq, (card, pl) in enumerate(zip(cards, pls), start=1):
        bankroll += pl
        peak = max(peak, bankroll)
        rows.append(
            {
                "strategy_name": strategy,
                "sequence": seq,
                "fight_id": f"f{card}",
                "fight_date": pd.Timestamp(dates[card]),
                "test_year": 2021,
                "fighter": f"A{card}",
                "opponent": f"B{card}",
                "actual_winner": f"A{card}",
                "role": "favorite" if card % 2 == 0 else "underdog",
                "is_main_card": card % 2 == 0,
                "model_prob": 0.6,
                "market_prob": 0.545,
                "edge": 0.055,
                "american_odds": -120,
                "decimal_odds": 1.833,
                "stake": 1.0,
                "won": pl > 0,
                "profit_loss": pl,
                "bankroll": bankroll,
                "drawdown": (bankroll - peak) / peak,
                "card_index": card,
            }
        )
    return pd.DataFrame(rows)


def test_card_month_quarter_grouping_is_deterministic() -> None:
    predictions = _predictions()

    assert len(build_windows(predictions, "card")) == 4
    assert [w.label for w in build_windows(predictions, "monthly")] == ["2021-01", "2021-02", "2021-04"]
    assert [w.label for w in build_windows(predictions, "quarterly")] == ["2021Q1", "2021Q2"]


def test_selection_uses_only_cards_before_test_window() -> None:
    predictions = _predictions()
    windows = build_windows(predictions, "card")
    logs = {
        "early_good": _log("early_good", [0, 1, 2, 3], [1.0, 1.0, -5.0, -5.0]),
        "future_good": _log("future_good", [0, 1, 2, 3], [-1.0, -1.0, 5.0, 5.0]),
    }
    history = StrategyHistory(logs, 4)

    selected = select_strategy(history, windows, 2, min_historical_bets=1, min_historical_windows=2)

    assert selected is not None
    assert selected["selected_strategy"] == "early_good"


def test_burnin_exclusion_breakdown_sums_match_total_bets() -> None:
    log = _log("strategy", [0, 1, 2], [1.0, -1.0, 1.0])
    rows = breakdown_rows({"strategy": log})
    role_rows = rows[rows["split_type"] == "favorite_underdog"]

    assert int(role_rows["bets"].sum()) == len(log)
    assert not _empty_log().columns.empty
