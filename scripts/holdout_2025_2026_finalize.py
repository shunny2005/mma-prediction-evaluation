#!/usr/bin/env python3
"""Part 15/17/19: build the consolidated data/ outputs (all_predictions.csv,
event_results.csv, model_vs_market.csv), the event-by-event table with cumulative
metrics, and per-event frozen prediction snapshot files.

Reproduce: PYTHONPATH=src .venv/bin/python scripts/holdout_2025_2026_finalize.py
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from mma_v4.core import expected_calibration_error, merge_local_odds, prediction_metrics
from mma_v4.paths import PROJECT_ROOT, V3_ODDS_MATCHED

OUT = PROJECT_ROOT / "holdout-2025-2026"
PRIMARY_SEED = 1701


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main() -> None:
    (OUT / "event_predictions").mkdir(parents=True, exist_ok=True)

    model = pd.read_csv(OUT / "data" / "event_retrained_all_predictions_multiseed.csv", low_memory=False)
    elo = pd.read_csv(OUT / "data" / "elo_only_event_retrained_all_predictions_multiseed.csv", low_memory=False)
    model_p = model[model.seed == PRIMARY_SEED].copy()
    elo_p = elo[elo.seed == PRIMARY_SEED].copy()

    tmp = model_p.copy()
    merged = merge_local_odds(tmp, V3_ODDS_MATCHED)

    def implied(o):
        return 100.0 / (o + 100.0) if o > 0 else (-o) / (-o + 100.0)

    merged["market_implied_p_a"] = np.where(merged["market_odds_available"], merged["fighter_1_odds"].map(implied), np.nan)
    merged["market_favorite_correct"] = np.where(merged["market_odds_available"], merged["market_favorite"] == merged["actual_winner"], np.nan)

    combined = merged.merge(elo_p[["fight_id", "fighter_a_win_probability", "prediction_correct"]].rename(
        columns={"fighter_a_win_probability": "elo_win_probability", "prediction_correct": "elo_correct"}), on="fight_id")

    # ---------------- data/all_predictions.csv ----------------
    all_preds_cols = [
        "fight_id", "event_name", "fight_date", "division", "fighter_a_name", "fighter_b_name",
        "fighter_a_id", "fighter_b_id", "actual_winner", "label_a_win",
        "fighter_a_win_probability", "predicted_winner", "prediction_correct",
        "elo_win_probability", "elo_correct",
        "market_odds_available", "market_favorite", "market_implied_p_a", "market_favorite_correct",
        "model_checkpoint", "latest_training_fight_date", "deployment_variant",
    ]
    combined[all_preds_cols].to_csv(OUT / "data" / "all_predictions.csv", index=False)

    # ---------------- data/model_vs_market.csv (matched subset only) ----------------
    matched = combined[combined["market_odds_available"] == True].copy()
    matched["fight_year"] = pd.to_datetime(matched["fight_date"]).dt.year
    matched.to_csv(OUT / "data" / "model_vs_market.csv", index=False)

    # ---------------- data/event_results.csv ----------------
    events_summary = []
    running_correct, running_n = 0, 0
    running_elo_correct = 0
    running_market_correct, running_market_n = 0, 0
    for (event_name, fight_date), g in combined.groupby(["event_name", "fight_date"], sort=False):
        pass
    events = combined[["event_name", "fight_date"]].drop_duplicates().copy()
    events["fight_date_dt"] = pd.to_datetime(events["fight_date"])
    events = events.sort_values("fight_date_dt").reset_index(drop=True)
    events["event_index"] = range(1, len(events) + 1)

    rows = []
    cum_correct = cum_n = cum_elo_correct = cum_market_correct = cum_market_n = 0
    cum_logloss_sum = 0.0
    for _, ev in events.iterrows():
        g = combined[(combined.event_name == ev.event_name) & (combined.fight_date == ev.fight_date)]
        gm = g[g["market_odds_available"] == True]
        n = len(g)
        correct = int(g["prediction_correct"].sum())
        elo_correct = int(g["elo_correct"].sum())
        market_correct = int(gm["market_favorite_correct"].sum()) if len(gm) else 0
        m = prediction_metrics(g["label_a_win"].to_numpy(float), g["fighter_a_win_probability"].to_numpy(float))
        cum_correct += correct
        cum_n += n
        cum_elo_correct += elo_correct
        cum_market_correct += market_correct
        cum_market_n += len(gm)
        rows.append({
            "event_index": ev.event_index, "event_name": ev.event_name, "fight_date": ev.fight_date,
            "fights": n, "model_correct": correct, "event_accuracy": correct / n if n else float("nan"),
            "elo_correct": elo_correct, "elo_accuracy": elo_correct / n if n else float("nan"),
            "matched_market_fights": len(gm),
            "market_correct": market_correct, "market_accuracy": market_correct / len(gm) if len(gm) else float("nan"),
            "cumulative_accuracy": cum_correct / cum_n if cum_n else float("nan"),
            "cumulative_elo_accuracy": cum_elo_correct / cum_n if cum_n else float("nan"),
            "cumulative_market_accuracy": cum_market_correct / cum_market_n if cum_market_n else float("nan"),
            "cumulative_log_loss": None,
        })
    events_df = pd.DataFrame(rows)
    # cumulative log loss computed separately (needs running pooled prediction concat)
    events_df["cumulative_log_loss"] = [
        prediction_metrics(
            combined[combined["fight_date"] <= events.iloc[i]["fight_date"]]["label_a_win"].to_numpy(float),
            combined[combined["fight_date"] <= events.iloc[i]["fight_date"]]["fighter_a_win_probability"].to_numpy(float),
        )["log_loss"]
        for i in range(len(events))
    ]
    events_df.to_csv(OUT / "data" / "event_results.csv", index=False)

    events_beat_market = int((events_df["event_accuracy"] > events_df["market_accuracy"]).sum())
    events_lost_to_market = int((events_df["event_accuracy"] < events_df["market_accuracy"]).sum())
    events_tied_market = int((events_df["event_accuracy"] == events_df["market_accuracy"]).sum())
    best_event = events_df.loc[events_df["event_accuracy"].idxmax()]
    worst_event = events_df.loc[events_df["event_accuracy"].idxmin()]
    print(f"Events: {len(events_df)}. Model beat market on {events_beat_market} events, lost on {events_lost_to_market}, tied on {events_tied_market}.")
    print(f"Best event: {best_event['event_name']} ({best_event['event_accuracy']:.2%}, n={best_event['fights']})")
    print(f"Worst event: {worst_event['event_name']} ({worst_event['event_accuracy']:.2%}, n={worst_event['fights']})")

    # ---------------- per-event frozen prediction snapshot files ----------------
    for _, ev in events.iterrows():
        g = combined[(combined.event_name == ev.event_name) & (combined.fight_date == ev.fight_date)]
        fname = f"{ev.fight_date}_{slugify(ev.event_name)}.csv"
        g[all_preds_cols].to_csv(OUT / "event_predictions" / fname, index=False)
    print(f"Wrote {len(events)} per-event frozen prediction files under holdout-2025-2026/event_predictions/")

    print("Wrote data/all_predictions.csv, data/model_vs_market.csv, data/event_results.csv")


if __name__ == "__main__":
    main()
