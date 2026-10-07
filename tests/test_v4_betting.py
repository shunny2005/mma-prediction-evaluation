from __future__ import annotations

import pandas as pd

from mma_v4.betting import (
    RuleConfig,
    american_implied_probability,
    american_profit_per_unit,
    bets_for_rule,
    prepare_betting_predictions,
    _side_candidates,
)


def test_american_odds_conversion() -> None:
    assert round(american_implied_probability(150), 6) == 0.4
    assert round(american_implied_probability(-200), 6) == 0.666667
    assert round(american_profit_per_unit(150), 6) == 1.5
    assert round(american_profit_per_unit(-200), 6) == 0.5


def test_betting_predictions_are_post_prediction_columns() -> None:
    raw = pd.DataFrame(
        [
            {
                "fight_id": "f1",
                "fight_date": "2021-01-01",
                "test_year": 2021,
                "fighter_a_name": "Alpha",
                "fighter_b_name": "Bravo",
                "fighter_a_win_probability": 0.62,
                "fighter_b_win_probability": 0.38,
                "actual_winner": "Alpha",
                "market_odds_available": True,
                "market_favorite": "Bravo",
                "fighter_1_odds": 120,
                "fighter_2_odds": -140,
            }
        ]
    )
    out = prepare_betting_predictions(raw)

    assert out.loc[0, "fighter_a"] == "Alpha"
    assert out.loc[0, "model_pick"] == "Alpha"
    assert round(out.loc[0, "implied_prob_a"], 6) == 0.454545
    assert round(out.loc[0, "model_edge_a"], 6) == 0.165455


def test_rule_selects_at_most_one_side_per_fight() -> None:
    raw = pd.DataFrame(
        [
            {
                "fight_id": "f1",
                "fight_date": "2021-01-01",
                "test_year": 2021,
                "fighter_a_name": "Alpha",
                "fighter_b_name": "Bravo",
                "fighter_a_win_probability": 0.62,
                "fighter_b_win_probability": 0.38,
                "actual_winner": "Alpha",
                "market_odds_available": True,
                "market_favorite": "Bravo",
                "fighter_1_odds": 120,
                "fighter_2_odds": -140,
            }
        ]
    )
    predictions = prepare_betting_predictions(raw)
    sides = _side_candidates(predictions)
    bets = bets_for_rule(sides, RuleConfig("edge", "edge_threshold", min_edge=0.01))

    assert len(bets) == 1
    assert bets.loc[0, "fighter"] == "Alpha"
