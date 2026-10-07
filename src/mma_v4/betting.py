from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mma_v4.main_card import annotate_main_card


BETTING_TEST_YEARS = list(range(2021, 2026))
STARTING_BANKROLL = 100.0


@dataclass(frozen=True)
class RuleConfig:
    name: str
    family: str
    min_edge: float | None = None
    min_prob: float | None = None
    side_filter: str = "any"
    model_market: str = "any"
    dog_cap: float | None = None
    stake_score: str | None = None
    min_stake_score: float | None = None


@dataclass(frozen=True)
class SizingConfig:
    name: str
    family: str
    value: float = 0.0
    multiplier: float = 0.0
    cap: float = 0.0
    shrink: float | None = None


def american_implied_probability(odds: float | int | str | None) -> float:
    if odds is None or pd.isna(odds):
        return np.nan
    odds_f = float(odds)
    if odds_f == 0:
        return np.nan
    if odds_f > 0:
        return 100.0 / (odds_f + 100.0)
    return abs(odds_f) / (abs(odds_f) + 100.0)


def american_profit_per_unit(odds: float | int | str | None) -> float:
    if odds is None or pd.isna(odds):
        return np.nan
    odds_f = float(odds)
    if odds_f == 0:
        return np.nan
    if odds_f > 0:
        return odds_f / 100.0
    return 100.0 / abs(odds_f)


def strategy_rules() -> list[RuleConfig]:
    rules: list[RuleConfig] = []
    for edge in [0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20]:
        rules.append(RuleConfig(f"edge_ge_{edge:g}", "edge_threshold", min_edge=edge))
    for prob in [0.55, 0.575, 0.60, 0.625, 0.65, 0.70]:
        rules.append(RuleConfig(f"confidence_ge_{prob:g}", "confidence_threshold", min_prob=prob))
    for edge in [0.03, 0.05, 0.075, 0.10]:
        for prob in [0.55, 0.60, 0.65]:
            rules.append(RuleConfig(f"favorite_edge_ge_{edge:g}_conf_ge_{prob:g}", "favorite_only", min_edge=edge, min_prob=prob, side_filter="favorite"))
    for edge in [0.03, 0.05, 0.075, 0.10]:
        for prob in [0.55, 0.60, 0.65]:
            for cap in [150.0, 200.0, 300.0, None]:
                cap_name = "no_cap" if cap is None else f"cap_plus_{int(cap)}"
                rules.append(RuleConfig(f"underdog_edge_ge_{edge:g}_conf_ge_{prob:g}_{cap_name}", "underdog_only", min_edge=edge, min_prob=prob, side_filter="underdog", dog_cap=cap))
    for edge in [0.10, 0.15, 0.20]:
        rules.append(RuleConfig(f"disagreement_edge_ge_{edge:g}", "model_market_disagreement", min_edge=edge, model_market="disagree"))
        rules.append(RuleConfig(f"disagreement_edge_ge_{edge:g}_conf_ge_0.55", "model_market_disagreement", min_edge=edge, min_prob=0.55, model_market="disagree"))
        rules.append(RuleConfig(f"disagreement_edge_ge_{edge:g}_conf_ge_0.60", "model_market_disagreement", min_edge=edge, min_prob=0.60, model_market="disagree"))
    for edge in [0.02, 0.03]:
        rules.append(RuleConfig(f"agreement_conf_ge_0.60_edge_ge_{edge:g}", "model_market_agreement", min_edge=edge, min_prob=0.60, model_market="agree"))
        rules.append(RuleConfig(f"agreement_favorite_conf_ge_0.60_edge_ge_{edge:g}", "model_market_agreement", min_edge=edge, min_prob=0.60, side_filter="favorite", model_market="agree"))
    score_thresholds = {
        "model_prob_x_edge": [0.015, 0.025, 0.04],
        "edge_over_market_prob": [0.05, 0.10, 0.20],
        "edge_x_decimal_odds": [0.05, 0.10, 0.20],
        "shrunk_prob_edge": [0.02, 0.03, 0.05],
    }
    for score_name, thresholds in score_thresholds.items():
        for threshold in thresholds:
            rules.append(RuleConfig(f"hedge_{score_name}_ge_{threshold:g}", "confidence_odds_hedge", stake_score=score_name, min_stake_score=threshold))
    return rules


def sizing_rules() -> list[SizingConfig]:
    sizes: list[SizingConfig] = []
    for units in [0.5, 1.0, 2.0]:
        sizes.append(SizingConfig(f"flat_{units:g}u", "flat", value=units))
    for frac in [0.0025, 0.005, 0.01, 0.02]:
        sizes.append(SizingConfig(f"bankroll_{frac * 100:g}pct", "percent_bankroll", value=frac))
    for mult in [0.5, 1.0, 2.0]:
        for cap in [0.005, 0.01, 0.02, 0.03]:
            sizes.append(SizingConfig(f"edge_prop_m{mult:g}_cap_{cap * 100:g}pct", "edge_proportional", multiplier=mult, cap=cap))
    for kelly in [0.10, 0.25, 0.50]:
        for cap in [0.005, 0.01, 0.02, 0.03]:
            sizes.append(SizingConfig(f"kelly_{kelly:g}_cap_{cap * 100:g}pct", "fractional_kelly", value=kelly, cap=cap))
    for shrink in [0.25, 0.50, 0.75]:
        for kelly in [0.10, 0.25, 0.50]:
            for cap in [0.005, 0.01, 0.02, 0.03]:
                sizes.append(SizingConfig(f"shrunk_kelly_s{shrink:g}_k{kelly:g}_cap_{cap * 100:g}pct", "shrunk_fractional_kelly", value=kelly, cap=cap, shrink=shrink))
    return sizes


def prepare_betting_predictions(predictions: pd.DataFrame, features: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = predictions.copy()
    frame["fight_date"] = pd.to_datetime(frame["fight_date"], errors="coerce")
    if "test_year" not in frame:
        frame["test_year"] = frame["fight_date"].dt.year
    frame = frame[frame["test_year"].isin(BETTING_TEST_YEARS)].copy()
    frame = frame[frame.get("market_odds_available", False) == True].copy()
    if features is not None:
        annotated, _ = annotate_main_card(features)
        main_lookup = annotated[["fight_id", "is_main_card"]].drop_duplicates("fight_id")
        frame = frame.merge(main_lookup, on="fight_id", how="left")
    if "is_main_card" not in frame:
        frame["is_main_card"] = False
    frame["is_main_card"] = frame["is_main_card"].fillna(False).astype(bool)
    frame["odds_a"] = pd.to_numeric(frame.get("fighter_1_odds"), errors="coerce")
    frame["odds_b"] = pd.to_numeric(frame.get("fighter_2_odds"), errors="coerce")
    frame["pred_prob_a"] = pd.to_numeric(frame["fighter_a_win_probability"], errors="coerce")
    frame["pred_prob_b"] = pd.to_numeric(frame["fighter_b_win_probability"], errors="coerce")
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
        "fight_id",
        "fight_date",
        "test_year",
        "fighter_a",
        "fighter_b",
        "pred_prob_a",
        "pred_prob_b",
        "actual_winner",
        "odds_a",
        "odds_b",
        "implied_prob_a",
        "implied_prob_b",
        "market_favorite",
        "model_pick",
        "model_confidence",
        "model_edge_a",
        "model_edge_b",
        "is_main_card",
        "profit_per_1_a",
        "profit_per_1_b",
        "decimal_odds_a",
        "decimal_odds_b",
    ]
    return frame.dropna(subset=["odds_a", "odds_b", "pred_prob_a", "pred_prob_b"])[required].sort_values(["fight_date", "fight_id"]).reset_index(drop=True)


def _side_candidates(predictions: pd.DataFrame) -> pd.DataFrame:
    common = ["fight_id", "fight_date", "test_year", "fighter_a", "fighter_b", "actual_winner", "market_favorite", "model_pick", "model_confidence", "is_main_card"]
    a = predictions[common].copy()
    a["side"] = "A"
    a["fighter"] = predictions["fighter_a"]
    a["opponent"] = predictions["fighter_b"]
    a["model_prob"] = predictions["pred_prob_a"]
    a["market_prob"] = predictions["implied_prob_a"]
    a["edge"] = predictions["model_edge_a"]
    a["american_odds"] = predictions["odds_a"]
    a["profit_per_1"] = predictions["profit_per_1_a"]
    a["decimal_odds"] = predictions["decimal_odds_a"]
    b = predictions[common].copy()
    b["side"] = "B"
    b["fighter"] = predictions["fighter_b"]
    b["opponent"] = predictions["fighter_a"]
    b["model_prob"] = predictions["pred_prob_b"]
    b["market_prob"] = predictions["implied_prob_b"]
    b["edge"] = predictions["model_edge_b"]
    b["american_odds"] = predictions["odds_b"]
    b["profit_per_1"] = predictions["profit_per_1_b"]
    b["decimal_odds"] = predictions["decimal_odds_b"]
    sides = pd.concat([a, b], ignore_index=True)
    sides["is_market_favorite"] = sides["fighter"] == sides["market_favorite"]
    sides["is_model_pick"] = sides["fighter"] == sides["model_pick"]
    sides["model_market_agree"] = sides["model_pick"] == sides["market_favorite"]
    sides["won"] = sides["fighter"] == sides["actual_winner"]
    sides["role"] = np.where(sides["is_market_favorite"], "favorite", "underdog")
    return sides


def _stake_score(frame: pd.DataFrame, name: str | None) -> pd.Series:
    if name is None:
        return pd.Series(0.0, index=frame.index)
    if name == "model_prob_x_edge":
        return frame["model_prob"] * frame["edge"]
    if name == "edge_over_market_prob":
        return frame["edge"] / frame["market_prob"].replace(0, np.nan)
    if name == "edge_x_decimal_odds":
        return frame["edge"] * frame["decimal_odds"]
    if name == "shrunk_prob_edge":
        return (0.5 + 0.5 * (frame["model_prob"] - 0.5)) - frame["market_prob"]
    raise ValueError(f"Unknown stake score: {name}")


def bets_for_rule(side_candidates: pd.DataFrame, rule: RuleConfig) -> pd.DataFrame:
    bets = side_candidates[side_candidates["is_model_pick"]].copy()
    if rule.min_edge is not None:
        bets = bets[bets["edge"] >= rule.min_edge]
    if rule.min_prob is not None:
        bets = bets[bets["model_prob"] >= rule.min_prob]
    if rule.side_filter == "favorite":
        bets = bets[bets["is_market_favorite"]]
    elif rule.side_filter == "underdog":
        bets = bets[~bets["is_market_favorite"]]
        if rule.dog_cap is not None:
            bets = bets[(bets["american_odds"] > 0) & (bets["american_odds"] <= rule.dog_cap)]
    if rule.model_market == "agree":
        bets = bets[bets["model_market_agree"]]
    elif rule.model_market == "disagree":
        bets = bets[~bets["model_market_agree"]]
    if rule.min_stake_score is not None:
        bets["stake_score"] = _stake_score(bets, rule.stake_score)
        bets = bets[bets["stake_score"] >= rule.min_stake_score]
    else:
        bets["stake_score"] = _stake_score(bets, rule.stake_score)
    return bets.sort_values(["fight_date", "fight_id"]).drop_duplicates("fight_id", keep="first").reset_index(drop=True)


def _kelly_fraction(model_prob: float, decimal_odds: float) -> float:
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    q = 1.0 - model_prob
    return max(0.0, (b * model_prob - q) / b)


def _stake_amount(bankroll: float, bet: pd.Series, sizing: SizingConfig) -> float:
    if bankroll <= 0:
        return 0.0
    if sizing.family == "flat":
        stake = sizing.value
    elif sizing.family == "percent_bankroll":
        stake = bankroll * sizing.value
    elif sizing.family == "edge_proportional":
        stake = bankroll * min(sizing.cap, max(0.0, float(bet["edge"]) * sizing.multiplier))
    elif sizing.family == "fractional_kelly":
        stake = bankroll * min(sizing.cap, _kelly_fraction(float(bet["model_prob"]), float(bet["decimal_odds"])) * sizing.value)
    elif sizing.family == "shrunk_fractional_kelly":
        prob = 0.5 + float(sizing.shrink or 0.0) * (float(bet["model_prob"]) - 0.5)
        stake = bankroll * min(sizing.cap, _kelly_fraction(prob, float(bet["decimal_odds"])) * sizing.value)
    else:
        raise ValueError(f"Unknown sizing family: {sizing.family}")
    return max(0.0, min(float(stake), bankroll))


def simulate_bets(bets: pd.DataFrame, sizing: SizingConfig, starting_bankroll: float = STARTING_BANKROLL, strategy_name: str = "") -> tuple[pd.DataFrame, dict[str, Any]]:
    bankroll = starting_bankroll
    peak = starting_bankroll
    rows: list[dict[str, Any]] = []
    for sequence, (_, bet) in enumerate(bets.sort_values(["fight_date", "fight_id"]).iterrows(), start=1):
        stake = _stake_amount(bankroll, bet, sizing)
        if stake <= 0:
            continue
        profit_loss = stake * float(bet["profit_per_1"]) if bool(bet["won"]) else -stake
        bankroll += profit_loss
        peak = max(peak, bankroll)
        drawdown = 0.0 if peak <= 0 else (bankroll - peak) / peak
        rows.append(
            {
                "strategy_name": strategy_name,
                "sequence": sequence,
                "fight_id": bet["fight_id"],
                "fight_date": bet["fight_date"],
                "test_year": int(bet["test_year"]),
                "fighter": bet["fighter"],
                "opponent": bet["opponent"],
                "actual_winner": bet["actual_winner"],
                "role": bet["role"],
                "is_main_card": bool(bet["is_main_card"]),
                "model_prob": float(bet["model_prob"]),
                "market_prob": float(bet["market_prob"]),
                "edge": float(bet["edge"]),
                "american_odds": float(bet["american_odds"]),
                "decimal_odds": float(bet["decimal_odds"]),
                "stake": stake,
                "won": bool(bet["won"]),
                "profit_loss": profit_loss,
                "bankroll": bankroll,
                "drawdown": drawdown,
            }
        )
    log = pd.DataFrame(rows)
    return log, summarize_bet_log(log, strategy_name, test_year="ALL", starting_bankroll=starting_bankroll)


def summarize_bet_log(log: pd.DataFrame, strategy_name: str, test_year: int | str, starting_bankroll: float = STARTING_BANKROLL) -> dict[str, Any]:
    if log.empty:
        return {
            "strategy_name": strategy_name,
            "test_year": test_year,
            "bets": 0,
            "wins": 0,
            "losses": 0,
            "pushes_no_contests": 0,
            "hit_rate": 0.0,
            "total_staked": 0.0,
            "profit_loss": 0.0,
            "roi": 0.0,
            "ending_bankroll": starting_bankroll,
            "max_drawdown": 0.0,
            "average_stake": 0.0,
            "median_stake": 0.0,
            "largest_stake": 0.0,
            "average_odds": 0.0,
            "average_model_prob": 0.0,
            "average_market_prob": 0.0,
            "average_edge": 0.0,
            "favorite_bets": 0,
            "underdog_bets": 0,
            "favorite_roi": 0.0,
            "underdog_roi": 0.0,
            "main_card_bets": 0,
            "main_card_roi": 0.0,
        }
    total_staked = float(log["stake"].sum())
    wins = int(log["won"].sum())
    fav = log[log["role"] == "favorite"]
    dog = log[log["role"] == "underdog"]
    main = log[log["is_main_card"]]
    return {
        "strategy_name": strategy_name,
        "test_year": test_year,
        "bets": int(len(log)),
        "wins": wins,
        "losses": int(len(log) - wins),
        "pushes_no_contests": 0,
        "hit_rate": round(wins / len(log), 6),
        "total_staked": round(total_staked, 6),
        "profit_loss": round(float(log["profit_loss"].sum()), 6),
        "roi": round(float(log["profit_loss"].sum()) / total_staked, 6) if total_staked else 0.0,
        "ending_bankroll": round(float(log["bankroll"].iloc[-1]), 6),
        "max_drawdown": round(float(log["drawdown"].min()), 6),
        "average_stake": round(float(log["stake"].mean()), 6),
        "median_stake": round(float(log["stake"].median()), 6),
        "largest_stake": round(float(log["stake"].max()), 6),
        "average_odds": round(float(log["american_odds"].mean()), 6),
        "average_model_prob": round(float(log["model_prob"].mean()), 6),
        "average_market_prob": round(float(log["market_prob"].mean()), 6),
        "average_edge": round(float(log["edge"].mean()), 6),
        "favorite_bets": int(len(fav)),
        "underdog_bets": int(len(dog)),
        "favorite_roi": round(float(fav["profit_loss"].sum()) / float(fav["stake"].sum()), 6) if len(fav) and fav["stake"].sum() else 0.0,
        "underdog_roi": round(float(dog["profit_loss"].sum()) / float(dog["stake"].sum()), 6) if len(dog) and dog["stake"].sum() else 0.0,
        "main_card_bets": int(len(main)),
        "main_card_roi": round(float(main["profit_loss"].sum()) / float(main["stake"].sum()), 6) if len(main) and main["stake"].sum() else 0.0,
    }


def evaluate_strategy_grid(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    sides = _side_candidates(predictions)
    grid_rows: list[dict[str, Any]] = []
    yearly_rows: list[dict[str, Any]] = []
    main_rows: list[dict[str, Any]] = []
    bet_logs: dict[str, pd.DataFrame] = {}
    for rule in strategy_rules():
        rule_bets = bets_for_rule(sides, rule)
        for sizing in sizing_rules():
            strategy_name = f"{rule.name}__{sizing.name}"
            log, all_summary = simulate_bets(rule_bets, sizing, strategy_name=strategy_name)
            all_summary.update({"rule_family": rule.family, "sizing_family": sizing.family})
            bet_logs[strategy_name] = log
            strategy_years: list[dict[str, Any]] = []
            for year in BETTING_TEST_YEARS:
                year_log = log[log["test_year"] == year].copy()
                if not year_log.empty:
                    year_log["bankroll"] = STARTING_BANKROLL + year_log["profit_loss"].cumsum()
                    year_log["drawdown"] = year_log["bankroll"] / year_log["bankroll"].cummax() - 1.0
                row = summarize_bet_log(year_log, strategy_name, year)
                row.update({"rule_family": rule.family, "sizing_family": sizing.family})
                strategy_years.append(row)
                yearly_rows.append(row)
            year_frame = pd.DataFrame(strategy_years)
            total_staked = float(all_summary["total_staked"])
            total_pl = float(all_summary["profit_loss"])
            all_summary.update(
                {
                    "total_bets": int(all_summary["bets"]),
                    "total_staked": round(total_staked, 6),
                    "total_profit_loss": round(total_pl, 6),
                    "overall_roi": round(total_pl / total_staked, 6) if total_staked else 0.0,
                    "annualized_like_return": round((float(all_summary["ending_bankroll"]) / STARTING_BANKROLL) ** (1.0 / len(BETTING_TEST_YEARS)) - 1.0, 6)
                    if float(all_summary["ending_bankroll"]) > 0
                    else -1.0,
                    "best_year": int(year_frame.sort_values("roi", ascending=False).iloc[0]["test_year"]) if not year_frame.empty else "",
                    "worst_year": int(year_frame.sort_values("roi", ascending=True).iloc[0]["test_year"]) if not year_frame.empty else "",
                    "yearly_roi_std": round(float(year_frame["roi"].std()), 6) if len(year_frame) > 1 else 0.0,
                }
            )
            grid_rows.append(all_summary)
            main_log = log[log["is_main_card"]].copy()
            if not main_log.empty:
                main_log["bankroll"] = STARTING_BANKROLL + main_log["profit_loss"].cumsum()
                main_log["drawdown"] = main_log["bankroll"] / main_log["bankroll"].cummax() - 1.0
            main = summarize_bet_log(main_log, strategy_name, "MAIN_CARD")
            main.update({"rule_family": rule.family, "sizing_family": sizing.family})
            main_rows.append(main)
    return pd.DataFrame(grid_rows), pd.DataFrame(yearly_rows), pd.DataFrame(main_rows), bet_logs


def favorite_underdog_breakdown(bet_logs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for strategy_name, log in bet_logs.items():
        if log.empty:
            for role in ["favorite", "underdog"]:
                row = summarize_bet_log(log, strategy_name, role)
                row["breakdown_role"] = role
                rows.append(row)
            continue
        for role in ["favorite", "underdog"]:
            part = log[log["role"] == role].copy()
            if not part.empty:
                part["bankroll"] = STARTING_BANKROLL + part["profit_loss"].cumsum()
                part["drawdown"] = part["bankroll"] / part["bankroll"].cummax() - 1.0
            row = summarize_bet_log(part, strategy_name, role)
            row["breakdown_role"] = role
            rows.append(row)
    return pd.DataFrame(rows)


def _markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> list[str]:
    if frame.empty:
        return ["_No rows available._"]
    shown = frame.head(max_rows).copy()
    columns = list(shown.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in shown.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return lines


def _selection_score(history: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        history.groupby("strategy_name")
        .agg(
            historical_bets=("bets", "sum"),
            historical_staked=("total_staked", "sum"),
            historical_profit_loss=("profit_loss", "sum"),
            historical_max_drawdown=("max_drawdown", "min"),
            positive_year_share=("roi", lambda s: float((s > 0).mean()) if len(s) else 0.0),
            yearly_roi_std=("roi", "std"),
        )
        .reset_index()
    )
    grouped["historical_roi"] = np.where(grouped["historical_staked"] > 0, grouped["historical_profit_loss"] / grouped["historical_staked"], 0.0)
    grouped["yearly_roi_std"] = grouped["yearly_roi_std"].fillna(0.0)
    grouped["selection_score"] = (
        grouped["historical_roi"]
        - grouped["historical_max_drawdown"].abs()
        - np.maximum(0.0, 30.0 - grouped["historical_bets"]) / 30.0 * 0.10
        - grouped["yearly_roi_std"] * 0.50
    )
    grouped["passes_constraints"] = (grouped["historical_bets"] >= 30) & (grouped["historical_max_drawdown"].abs() <= 0.30) & (grouped["positive_year_share"] >= 0.50)
    return grouped.sort_values(["passes_constraints", "selection_score", "historical_bets"], ascending=[False, False, False])


def walk_forward_strategy_selection(yearly: pd.DataFrame, bet_logs: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    default_strategy = "edge_ge_0.05__flat_1u"
    selection_rows: list[dict[str, Any]] = []
    selected_summaries: list[dict[str, Any]] = []
    selected_logs: list[pd.DataFrame] = []
    for year in BETTING_TEST_YEARS:
        if year == BETTING_TEST_YEARS[0]:
            selected = default_strategy
            basis = "predefined_conservative_default"
            score_row: dict[str, Any] = {}
        else:
            historical = yearly[yearly["test_year"].isin([y for y in BETTING_TEST_YEARS if y < year])].copy()
            scored = _selection_score(historical)
            selected = str(scored.iloc[0]["strategy_name"]) if not scored.empty else default_strategy
            basis = f"prior_years_{BETTING_TEST_YEARS[0]}_{year - 1}"
            score_row = scored.iloc[0].to_dict() if not scored.empty else {}
        log = bet_logs.get(selected, pd.DataFrame()).copy()
        year_log = log[log["test_year"] == year].copy()
        if not year_log.empty:
            year_log["bankroll"] = STARTING_BANKROLL + year_log["profit_loss"].cumsum()
            year_log["drawdown"] = year_log["bankroll"] / year_log["bankroll"].cummax() - 1.0
            year_log["selected_for_year"] = year
            selected_logs.append(year_log)
        summary = summarize_bet_log(year_log, selected, year)
        selected_summaries.append(summary)
        selection_rows.append(
            {
                "test_year": year,
                "selected_strategy": selected,
                "selection_basis": basis,
                "historical_bets": score_row.get("historical_bets", ""),
                "historical_roi": score_row.get("historical_roi", ""),
                "historical_max_drawdown": score_row.get("historical_max_drawdown", ""),
                "positive_year_share": score_row.get("positive_year_share", ""),
                "yearly_roi_std": score_row.get("yearly_roi_std", ""),
                "selection_score": score_row.get("selection_score", ""),
            }
        )
    selected_log = pd.concat(selected_logs, ignore_index=True) if selected_logs else pd.DataFrame()
    return pd.DataFrame(selection_rows), pd.DataFrame(selected_summaries), selected_log


def write_markdown_reports(output_dir: Path, predictions: pd.DataFrame, grid: pd.DataFrame, yearly: pd.DataFrame, selection: pd.DataFrame, selected_yearly: pd.DataFrame) -> None:
    top = grid[grid["bets"] >= 30].sort_values("profit_loss", ascending=False).head(10)
    selected_total_staked = float(selected_yearly["total_staked"].sum()) if not selected_yearly.empty else 0.0
    selected_total_pl = float(selected_yearly["profit_loss"].sum()) if not selected_yearly.empty else 0.0
    selected_roi = selected_total_pl / selected_total_staked if selected_total_staked else 0.0
    lines = [
        "# V4 Betting Rule Research Summary",
        "",
        "Research-only historical evaluation. No live betting, scraping, order execution, or sportsbook integration is included.",
        "",
        "## Data",
        "",
        f"- Active prediction source: model_v4_active / active_feature_set.",
        f"- Betting years: {BETTING_TEST_YEARS[0]}-{BETTING_TEST_YEARS[-1]}.",
        f"- Fights with usable odds after prediction merge: {len(predictions)}.",
        "- Odds are evaluation inputs only and are merged after model probabilities exist.",
        "",
        "## Walk-Forward Selected Strategy",
        "",
        f"- Total staked: {selected_total_staked:.2f} units.",
        f"- Profit/loss: {selected_total_pl:.2f} units.",
        f"- ROI: {selected_roi:.2%}.",
        "",
        *_markdown_table(selection),
        "",
        "## Exploratory Full-Sample Grid",
        "",
        "The following table is exploratory because it ranks strategies using the full 2021-2025 sample.",
        "",
        *_markdown_table(top[["strategy_name", "bets", "profit_loss", "roi", "max_drawdown", "favorite_bets", "underdog_bets", "main_card_bets"]]),
        "",
    ]
    (output_dir / "BETTING_RESEARCH_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    audit = [
        "# Leakage And Overfitting Audit",
        "",
        "- The betting module consumes already-created walk-forward prediction rows.",
        "- Odds columns are not passed into `numeric_feature_columns` or model training.",
        "- Historical odds are converted only after predictions are loaded.",
        "- Full-grid rankings are labeled exploratory and should not be read as out-of-sample strategy selection.",
        "- Walk-forward strategy selection for each year uses only prior betting years, with 2021 using a predefined conservative default.",
        "- Main-card-only results are evaluation subsets; no separate main-card betting model is trained.",
        "- The current module does not place both sides of a fight; hedge-style rules mean risk-adjusted sizing/filtering only.",
        "- Kelly staking is fractional and capped.",
    ]
    (output_dir / "LEAKAGE_AND_OVERFITTING_AUDIT.md").write_text("\n".join(audit), encoding="utf-8")


def run_betting_research(predictions_path: Path, features_path: Path, output_dir: Path) -> dict[str, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = pd.read_csv(predictions_path, low_memory=False)
    features = pd.read_csv(features_path, low_memory=False)
    betting_predictions = prepare_betting_predictions(predictions, features)
    grid, yearly, main_card, bet_logs = evaluate_strategy_grid(betting_predictions)
    selection, selected_yearly, selected_log = walk_forward_strategy_selection(yearly, bet_logs)
    breakdown = favorite_underdog_breakdown(bet_logs)
    drawdowns = selected_log[["selected_for_year", "strategy_name", "sequence", "fight_date", "test_year", "bankroll", "drawdown"]].copy() if not selected_log.empty else pd.DataFrame()
    betting_predictions.to_csv(output_dir / "betting_predictions_with_odds.csv", index=False)
    grid.to_csv(output_dir / "strategy_grid_results.csv", index=False)
    yearly.to_csv(output_dir / "yearly_strategy_results.csv", index=False)
    selection.to_csv(output_dir / "walk_forward_strategy_selection.csv", index=False)
    selected_yearly.to_csv(output_dir / "selected_strategy_yearly_results.csv", index=False)
    selected_log.to_csv(output_dir / "selected_strategy_bet_log.csv", index=False)
    main_card.to_csv(output_dir / "main_card_strategy_results.csv", index=False)
    breakdown.to_csv(output_dir / "favorite_underdog_strategy_breakdown.csv", index=False)
    drawdowns.to_csv(output_dir / "drawdown_curves.csv", index=False)
    write_markdown_reports(output_dir, betting_predictions, grid, yearly, selection, selected_yearly)
    return {
        "betting_predictions": betting_predictions,
        "strategy_grid": grid,
        "yearly": yearly,
        "selection": selection,
        "selected_yearly": selected_yearly,
        "selected_log": selected_log,
        "main_card": main_card,
        "breakdown": breakdown,
        "drawdowns": drawdowns,
    }
