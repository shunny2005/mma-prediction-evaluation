#!/usr/bin/env python3
"""Part 12: rerun the previously-locked resume betting strategies on the strictly
pre-event 2025-2026 predictions. No thresholds are tuned here -- every rule/sizing
config is taken verbatim from mma_v4.betting.strategy_rules()/sizing_rules() by its
already-published name.

Reuses the project's own mechanical bet-simulation functions (bets_for_rule,
simulate_bets) directly -- these have no year dependency. The higher-level
run_betting_research()/run_rolling_walk_forward() wrappers were NOT reused because they
hardcode BETTING_TEST_YEARS = range(2021, 2026), which would silently drop every 2026
fight and mislabel 2025 as a "burn-in" year with no prior history (wrong for this
holdout, which has extensive already-computed 2018-2024 history to draw on) -- reusing
them would require either monkey-patching shared module state or accepting silently
wrong results, so a small purpose-built driver was written around the same mechanical
functions instead.

The locked quarterly selector is reproduced in spirit (score candidates using only
strictly-prior data, require a minimum evidence bar, re-select each quarter) but is
freshly bootstrapped within the 2025-2026 window rather than carrying forward the exact
internal state of the original 2018-2024 selector -- disclosed explicitly in
BETTING_RESULTS.md as a scoped simplification, not presented as bit-identical to the
original mechanism.

Reproduce: PYTHONPATH=src .venv/bin/python scripts/holdout_2025_2026_betting.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mma_v4.betting import (
    RuleConfig,
    SizingConfig,
    american_implied_probability,
    american_profit_per_unit,
    bets_for_rule,
    simulate_bets,
    _side_candidates,
)
from mma_v4.core import merge_local_odds
from mma_v4.paths import PROJECT_ROOT, V3_ODDS_MATCHED

OUT = PROJECT_ROOT / "holdout-2025-2026"
PRIMARY_SEED = 1701

LOCKED_FIXED_STRATEGIES = [
    ("confidence_ge_0.6__shrunk_kelly_s0.5_k0.25_cap_0.5pct", RuleConfig("confidence_ge_0.6", "confidence_threshold", min_prob=0.60), SizingConfig("shrunk_kelly_s0.5_k0.25_cap_0.5pct", "shrunk_fractional_kelly", value=0.25, cap=0.005, shrink=0.5)),
    ("underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct", RuleConfig("underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150", "underdog_only", min_edge=0.03, min_prob=0.55, side_filter="underdog", dog_cap=150.0), SizingConfig("bankroll_0.25pct", "percent_bankroll", value=0.0025)),
    ("favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct", RuleConfig("favorite_edge_ge_0.075_conf_ge_0.65", "favorite_only", min_edge=0.075, min_prob=0.65, side_filter="favorite"), SizingConfig("bankroll_0.25pct", "percent_bankroll", value=0.0025)),
    ("edge_ge_0.05__flat_1u", RuleConfig("edge_ge_0.05", "edge_threshold", min_edge=0.05), SizingConfig("flat_1u", "flat", value=1.0)),
]


def prepare_predictions_no_year_filter(predictions: pd.DataFrame) -> pd.DataFrame:
    """Same transformation as mma_v4.betting.prepare_betting_predictions, minus the
    BETTING_TEST_YEARS filter (which would wrongly drop every 2026 fight)."""
    frame = predictions.copy()
    frame["fight_date"] = pd.to_datetime(frame["fight_date"], errors="coerce")
    frame["test_year"] = frame["fight_date"].dt.year
    frame = frame[frame.get("market_odds_available", False) == True].copy()
    frame["is_main_card"] = False  # not reconstructed for this holdout; disclosed in BETTING_RESULTS.md
    frame["odds_a"] = pd.to_numeric(frame.get("fighter_1_odds"), errors="coerce")
    frame["odds_b"] = pd.to_numeric(frame.get("fighter_2_odds"), errors="coerce")
    frame["pred_prob_a"] = pd.to_numeric(frame["fighter_a_win_probability"], errors="coerce")
    frame["pred_prob_b"] = 1.0 - frame["pred_prob_a"]
    frame["implied_prob_a"] = frame["odds_a"].map(american_implied_probability)
    frame["implied_prob_b"] = frame["odds_b"].map(american_implied_probability)
    frame["profit_per_1_a"] = frame["odds_a"].map(american_profit_per_unit)
    frame["profit_per_1_b"] = frame["odds_b"].map(american_profit_per_unit)
    frame["decimal_odds_a"] = frame["profit_per_1_a"] + 1.0
    frame["decimal_odds_b"] = frame["profit_per_1_b"] + 1.0
    frame["model_edge_a"] = frame["pred_prob_a"] - frame["implied_prob_a"]
    frame["model_edge_b"] = frame["pred_prob_b"] - frame["implied_prob_b"]
    frame["fighter_a"] = frame["fighter_a_name"]
    frame["fighter_b"] = frame["fighter_b_name"]
    frame["model_pick"] = np.where(frame["pred_prob_a"] >= frame["pred_prob_b"], frame["fighter_a"], frame["fighter_b"])
    frame["model_confidence"] = frame[["pred_prob_a", "pred_prob_b"]].max(axis=1)
    frame["market_favorite"] = frame["market_favorite"].fillna("")
    required = [
        "fight_id", "fight_date", "test_year", "fighter_a", "fighter_b", "pred_prob_a", "pred_prob_b",
        "actual_winner", "odds_a", "odds_b", "implied_prob_a", "implied_prob_b", "market_favorite",
        "model_pick", "model_confidence", "model_edge_a", "model_edge_b", "is_main_card",
        "profit_per_1_a", "profit_per_1_b", "decimal_odds_a", "decimal_odds_b",
    ]
    return frame.dropna(subset=["odds_a", "odds_b", "pred_prob_a", "pred_prob_b"])[required].sort_values(["fight_date", "fight_id"]).reset_index(drop=True)


def summarize(log: pd.DataFrame, name: str) -> dict:
    if log.empty:
        return {"strategy": name, "eligible_fights": 0, "bets": 0, "wins": 0, "losses": 0, "units_wagered": 0.0, "units_won_lost": 0.0, "roi": float("nan"), "max_drawdown": 0.0, "average_odds": float("nan")}
    wins = int(log["won"].sum())
    losses = len(log) - wins
    units_wagered = float(log["stake"].sum())
    units_won_lost = float(log["profit_loss"].sum())
    roi = units_won_lost / units_wagered if units_wagered else float("nan")
    running_peak = log["bankroll"].cummax()
    drawdown = ((log["bankroll"] - running_peak) / running_peak.replace(0, np.nan)).min()
    return {
        "strategy": name, "bets": len(log), "wins": wins, "losses": losses, "win_rate": wins / len(log),
        "units_wagered": units_wagered, "units_won_lost": units_won_lost, "roi": roi,
        "max_drawdown": float(drawdown) if pd.notna(drawdown) else 0.0, "average_odds": float(log["american_odds"].mean()),
    }


def run_fixed_strategy(prepared: pd.DataFrame, name: str, rule: RuleConfig, sizing: SizingConfig) -> pd.DataFrame:
    candidates = _side_candidates(prepared)
    bets = bets_for_rule(candidates, rule)
    log, _ = simulate_bets(bets, sizing, strategy_name=name)
    return log


def run_locked_quarterly_selector(prepared: pd.DataFrame) -> pd.DataFrame:
    """Freshly bootstrapped within the holdout window: each quarter, score every
    (rule, sizing) combo among the 4 fixed candidates above (the same candidate set the
    original locked selector was built from) using ONLY bets from strictly prior
    quarters within this holdout, require >=15 historical bets before a candidate is
    eligible (scaled down from the original >=50 threshold, since a single-quarter slice
    of this smaller holdout can't produce 50 bets from only 1-3 prior quarters -- this
    relaxation is disclosed, not hidden), and default to the flat broad-edge rule during
    the first quarter with no eligible history."""
    prepared = prepared.copy()
    prepared["quarter"] = pd.to_datetime(prepared["fight_date"]).dt.to_period("Q")
    quarters = sorted(prepared["quarter"].unique())
    all_logs = []
    history_logs: dict[str, pd.DataFrame] = {name: pd.DataFrame() for name, _, _ in LOCKED_FIXED_STRATEGIES}
    for q in quarters:
        q_data = prepared[prepared["quarter"] == q]
        candidates_scores = {}
        for name, rule, sizing in LOCKED_FIXED_STRATEGIES:
            hist = history_logs[name]
            if len(hist) >= 15:
                candidates_scores[name] = float(hist["profit_loss"].sum() / hist["stake"].sum()) if hist["stake"].sum() else -999
        if candidates_scores:
            selected_name = max(candidates_scores, key=candidates_scores.get)
        else:
            selected_name = "edge_ge_0.05__flat_1u"  # documented default during no-history burn-in, same spirit as the original
        rule, sizing = next((r, s) for n, r, s in LOCKED_FIXED_STRATEGIES if n == selected_name)
        candidates = _side_candidates(q_data)
        bets = bets_for_rule(candidates, rule)
        log, _ = simulate_bets(bets, sizing, strategy_name=f"locked_quarterly[{selected_name}]")
        log["quarter"] = str(q)
        log["selected_strategy"] = selected_name
        all_logs.append(log)
        for name, rule2, sizing2 in LOCKED_FIXED_STRATEGIES:
            candidates_full = _side_candidates(q_data)
            bets_full = bets_for_rule(candidates_full, rule2)
            log_full, _ = simulate_bets(bets_full, sizing2, strategy_name=name)
            history_logs[name] = pd.concat([history_logs[name], log_full], ignore_index=True)
    return pd.concat(all_logs, ignore_index=True) if all_logs else pd.DataFrame()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    preds = pd.read_csv(OUT / "data" / "event_retrained_all_predictions_multiseed.csv", low_memory=False)
    preds = preds[preds["seed"] == PRIMARY_SEED].copy()
    merged = merge_local_odds(preds, V3_ODDS_MATCHED)
    prepared = prepare_predictions_no_year_filter(merged)
    print(f"{len(prepared)} eligible (odds-matched) fights for betting evaluation.")

    all_results = []
    all_logs = []
    for name, rule, sizing in LOCKED_FIXED_STRATEGIES:
        log = run_fixed_strategy(prepared, name, rule, sizing)
        summary = summarize(log, name)
        summary["eligible_fights"] = len(prepared)
        for period, yr in [("2025", 2025), ("2026", 2026)]:
            sub = log[pd.to_datetime(log["fight_date"]).dt.year == yr] if not log.empty else log
            wagered = float(sub["stake"].sum()) if not sub.empty else 0.0
            won = float(sub["profit_loss"].sum()) if not sub.empty else 0.0
            summary[f"{period}_bets"] = len(sub)
            summary[f"{period}_roi"] = won / wagered if wagered else float("nan")
        all_results.append(summary)
        all_logs.append(log.assign(strategy=name) if not log.empty else log)
        print(f"  {name:70s} bets={summary['bets']:4d} roi={summary.get('roi', float('nan')):+.4f} "
              f"units={summary['units_won_lost']:+.2f}")

    print("\n=== Locked quarterly selector (freshly bootstrapped, see docstring) ===")
    quarterly_log = run_locked_quarterly_selector(prepared)
    quarterly_summary = summarize(quarterly_log, "locked_quarterly_selector")
    quarterly_summary["eligible_fights"] = len(prepared)
    for period, yr in [("2025", 2025), ("2026", 2026)]:
        sub = quarterly_log[pd.to_datetime(quarterly_log["fight_date"]).dt.year == yr] if not quarterly_log.empty else quarterly_log
        wagered = float(sub["stake"].sum()) if not sub.empty else 0.0
        won = float(sub["profit_loss"].sum()) if not sub.empty else 0.0
        quarterly_summary[f"{period}_bets"] = len(sub)
        quarterly_summary[f"{period}_roi"] = won / wagered if wagered else float("nan")
    all_results.append(quarterly_summary)
    print(f"  bets={quarterly_summary['bets']} roi={quarterly_summary.get('roi', float('nan')):+.4f} "
          f"units={quarterly_summary['units_won_lost']:+.2f}")
    if not quarterly_log.empty:
        quarterly_log.to_csv(OUT / "data" / "locked_quarterly_selector_bet_log.csv", index=False)

    results_df = pd.DataFrame(all_results)
    results_df.to_csv(OUT / "data" / "betting_results.csv", index=False)
    combined_logs = pd.concat([l for l in all_logs if l is not None and not l.empty], ignore_index=True) if any(l is not None and not l.empty for l in all_logs) else pd.DataFrame()
    if not combined_logs.empty:
        combined_logs.to_csv(OUT / "data" / "betting_bet_log_fixed_strategies.csv", index=False)

    print("\nWrote holdout-2025-2026/data/betting_results.csv and bet logs.")


if __name__ == "__main__":
    main()
