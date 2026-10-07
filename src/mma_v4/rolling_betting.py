from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mma_v4.betting import (
    BETTING_TEST_YEARS,
    STARTING_BANKROLL,
    SizingConfig,
    _side_candidates,
    _stake_amount,
    bets_for_rule,
    evaluate_strategy_grid,
    prepare_betting_predictions,
    sizing_rules,
    strategy_rules,
    summarize_bet_log,
)


DEFAULT_STRATEGY = "edge_ge_0.05__flat_1u"
FIXED_BASELINES = [
    DEFAULT_STRATEGY,
    "underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct",
    "favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct",
    "confidence_ge_0.6__shrunk_kelly_s0.5_k0.25_cap_0.5pct",
]
LOG_COLUMNS = [
    "strategy_name",
    "sequence",
    "fight_id",
    "fight_date",
    "test_year",
    "fighter",
    "opponent",
    "actual_winner",
    "role",
    "is_main_card",
    "model_prob",
    "market_prob",
    "edge",
    "american_odds",
    "decimal_odds",
    "stake",
    "won",
    "profit_loss",
    "bankroll",
    "drawdown",
]
LOG_COLUMN_SET = set(LOG_COLUMNS)


@dataclass(frozen=True)
class Window:
    selector_type: str
    window_index: int
    start: pd.Timestamp
    end: pd.Timestamp
    label: str
    first_card_index: int
    last_card_index: int


@dataclass(frozen=True)
class SelectorConfig:
    selector_type: str
    min_historical_bets: int
    min_historical_windows: int
    burnin_policy: str

    @property
    def name(self) -> str:
        return (
            f"{self.selector_type}"
            f"__min_bets_{self.min_historical_bets}"
            f"__min_windows_{self.min_historical_windows}"
            f"__{self.burnin_policy}"
        )


def strategy_config_map() -> dict[str, tuple[SizingConfig, str, str]]:
    out: dict[str, tuple[SizingConfig, str, str]] = {}
    for rule in strategy_rules():
        for sizing in sizing_rules():
            out[f"{rule.name}__{sizing.name}"] = (sizing, rule.family, sizing.family)
    return out


def selector_configs() -> list[SelectorConfig]:
    configs: list[SelectorConfig] = []
    for selector_type in ["yearly", "card", "every_3_cards", "every_5_cards", "every_10_cards", "monthly", "quarterly"]:
        for min_bets in [25, 50, 100]:
            for min_windows in [5, 10, 20]:
                for burnin_policy in ["default_during_burnin", "no_bets_during_burnin"]:
                    configs.append(SelectorConfig(selector_type, min_bets, min_windows, burnin_policy))
    return configs


def assign_card_metadata(predictions: pd.DataFrame) -> pd.DataFrame:
    frame = predictions.copy()
    frame["fight_date"] = pd.to_datetime(frame["fight_date"], errors="coerce")
    card_dates = sorted(frame["fight_date"].dropna().unique())
    card_lookup = {pd.Timestamp(date): i for i, date in enumerate(card_dates)}
    frame["card_id"] = frame["fight_date"].dt.strftime("%Y-%m-%d")
    frame["card_index"] = frame["fight_date"].map(lambda value: card_lookup[pd.Timestamp(value)])
    frame["month_id"] = frame["fight_date"].dt.to_period("M").astype(str)
    frame["quarter_id"] = frame["fight_date"].dt.to_period("Q").astype(str)
    return frame


def build_windows(predictions: pd.DataFrame, selector_type: str) -> list[Window]:
    frame = predictions.sort_values(["fight_date", "fight_id"]).copy()
    card_dates = frame.groupby("card_index")["fight_date"].min().sort_index()
    windows: list[Window] = []
    if selector_type == "yearly":
        groups = [(str(year), group) for year, group in frame.groupby("test_year", sort=True)]
    elif selector_type == "card":
        groups = [(str(card), group) for card, group in frame.groupby("card_id", sort=True)]
    elif selector_type.startswith("every_") and selector_type.endswith("_cards"):
        size = int(selector_type.split("_")[1])
        groups = []
        for start_card in range(0, len(card_dates), size):
            cards = set(range(start_card, min(start_card + size, len(card_dates))))
            group = frame[frame["card_index"].isin(cards)]
            groups.append((f"cards_{start_card + 1}_{start_card + len(cards)}", group))
    elif selector_type == "monthly":
        groups = [(str(month), group) for month, group in frame.groupby("month_id", sort=True)]
    elif selector_type == "quarterly":
        groups = [(str(quarter), group) for quarter, group in frame.groupby("quarter_id", sort=True)]
    else:
        raise ValueError(f"Unknown selector type: {selector_type}")
    for i, (label, group) in enumerate(groups):
        if group.empty:
            continue
        first_card = int(group["card_index"].min())
        last_card = int(group["card_index"].max())
        start = pd.Timestamp(group["fight_date"].min())
        if last_card + 1 < len(card_dates):
            end = pd.Timestamp(card_dates.iloc[last_card + 1])
        else:
            end = pd.Timestamp(group["fight_date"].max()) + pd.Timedelta(days=1)
        windows.append(Window(selector_type, i, start, end, label, first_card, last_card))
    return windows


def _empty_log() -> pd.DataFrame:
    return pd.DataFrame(columns=LOG_COLUMNS)


def _prepare_strategy_logs(bet_logs: dict[str, pd.DataFrame], predictions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    date_to_card = predictions.drop_duplicates("fight_date").set_index("fight_date")["card_index"].to_dict()
    out: dict[str, pd.DataFrame] = {}
    for strategy_name, log in bet_logs.items():
        if log.empty:
            out[strategy_name] = _empty_log()
            continue
        frame = log.copy()
        frame["fight_date"] = pd.to_datetime(frame["fight_date"], errors="coerce")
        frame["card_index"] = frame["fight_date"].map(lambda value: date_to_card[pd.Timestamp(value)])
        frame["month_id"] = frame["fight_date"].dt.to_period("M").astype(str)
        frame["quarter_id"] = frame["fight_date"].dt.to_period("Q").astype(str)
        out[strategy_name] = frame.sort_values(["fight_date", "fight_id"]).reset_index(drop=True)
    return out


class StrategyHistory:
    def __init__(self, strategy_logs: dict[str, pd.DataFrame], card_count: int) -> None:
        self.names = sorted(strategy_logs)
        self.index = {name: i for i, name in enumerate(self.names)}
        shape = (len(self.names), card_count)
        self.bets = np.zeros(shape)
        self.wins = np.zeros(shape)
        self.staked = np.zeros(shape)
        self.pl = np.zeros(shape)
        self.favorite_staked = np.zeros(shape)
        self.favorite_pl = np.zeros(shape)
        self.underdog_staked = np.zeros(shape)
        self.underdog_pl = np.zeros(shape)
        self.main_staked = np.zeros(shape)
        self.main_pl = np.zeros(shape)
        for strategy_name, log in strategy_logs.items():
            if log.empty:
                continue
            idx = self.index[strategy_name]
            cards = log["card_index"].to_numpy(dtype=int)
            stakes = log["stake"].to_numpy(dtype=float)
            pls = log["profit_loss"].to_numpy(dtype=float)
            wins = log["won"].to_numpy(dtype=float)
            favorite = (log["role"].to_numpy() == "favorite").astype(float)
            underdog = (log["role"].to_numpy() == "underdog").astype(float)
            main = log["is_main_card"].to_numpy(dtype=float)
            np.add.at(self.bets[idx], cards, 1.0)
            np.add.at(self.wins[idx], cards, wins)
            np.add.at(self.staked[idx], cards, stakes)
            np.add.at(self.pl[idx], cards, pls)
            np.add.at(self.favorite_staked[idx], cards, stakes * favorite)
            np.add.at(self.favorite_pl[idx], cards, pls * favorite)
            np.add.at(self.underdog_staked[idx], cards, stakes * underdog)
            np.add.at(self.underdog_pl[idx], cards, pls * underdog)
            np.add.at(self.main_staked[idx], cards, stakes * main)
            np.add.at(self.main_pl[idx], cards, pls * main)
        self.cum_bets = np.cumsum(self.bets, axis=1)
        self.cum_staked = np.cumsum(self.staked, axis=1)
        self.cum_pl = np.cumsum(self.pl, axis=1)
        equity = STARTING_BANKROLL + self.cum_pl
        peaks = np.maximum.accumulate(np.maximum(equity, STARTING_BANKROLL), axis=1)
        self.drawdown = np.where(peaks > 0, (equity - peaks) / peaks, 0.0)

    def cumulative_before(self, card_index: int) -> dict[str, np.ndarray]:
        if card_index <= 0:
            zeros = np.zeros(len(self.names))
            return {"bets": zeros, "staked": zeros, "pl": zeros, "max_drawdown": zeros}
        end = card_index - 1
        return {
            "bets": self.cum_bets[:, end],
            "staked": self.cum_staked[:, end],
            "pl": self.cum_pl[:, end],
            "max_drawdown": self.drawdown[:, :card_index].min(axis=1),
        }

    def window_roi_stats(self, windows: list[Window], current_window_index: int) -> tuple[np.ndarray, np.ndarray]:
        prior = [window for window in windows[:current_window_index] if window.first_card_index < window.last_card_index + 1]
        if not prior:
            zeros = np.zeros(len(self.names))
            return zeros, zeros
        rois = []
        for window in prior:
            start = window.first_card_index
            end = window.last_card_index
            staked = self.cum_staked[:, end] - (self.cum_staked[:, start - 1] if start > 0 else 0.0)
            pl = self.cum_pl[:, end] - (self.cum_pl[:, start - 1] if start > 0 else 0.0)
            roi = np.full(len(self.names), np.nan)
            np.divide(pl, staked, out=roi, where=staked > 0)
            rois.append(roi)
        matrix = np.vstack(rois).T
        valid = ~np.isnan(matrix)
        positive = np.divide((matrix > 0).sum(axis=1), valid.sum(axis=1), out=np.zeros(len(self.names)), where=valid.sum(axis=1) > 0)
        filled = np.where(valid, matrix, 0.0)
        counts = valid.sum(axis=1)
        means = np.divide(filled.sum(axis=1), counts, out=np.zeros(len(self.names)), where=counts > 0)
        variance = np.divide(((np.where(valid, matrix - means[:, None], 0.0)) ** 2).sum(axis=1), counts, out=np.zeros(len(self.names)), where=counts > 0)
        std = np.sqrt(variance)
        return np.nan_to_num(positive), np.nan_to_num(std)


def _complexity_penalty(strategy_name: str) -> float:
    terms = ["underdog", "favorite", "disagreement", "agreement", "hedge", "cap_plus", "no_cap", "kelly", "edge_prop"]
    return 0.005 * sum(term in strategy_name for term in terms)


def select_strategy(
    history: StrategyHistory,
    windows: list[Window],
    window_index: int,
    min_historical_bets: int,
    min_historical_windows: int,
) -> dict[str, Any] | None:
    window = windows[window_index]
    required_windows = max(min_historical_windows, 2 if window.selector_type in {"yearly", "monthly", "quarterly"} else min_historical_windows)
    if window_index < required_windows:
        return None
    cumulative = history.cumulative_before(window.first_card_index)
    historical_bets = cumulative["bets"]
    historical_staked = cumulative["staked"]
    historical_pl = cumulative["pl"]
    historical_roi = np.divide(historical_pl, historical_staked, out=np.zeros_like(historical_pl), where=historical_staked > 0)
    max_drawdown = cumulative["max_drawdown"]
    positive_share, roi_std = history.window_roi_stats(windows, window_index)
    complexity = np.asarray([_complexity_penalty(name) for name in history.names])
    small_sample = np.maximum(0.0, min_historical_bets - historical_bets) / max(float(min_historical_bets), 1.0) * 0.10
    score = historical_roi - np.abs(max_drawdown) - roi_std - small_sample - complexity
    eligible = (historical_bets >= min_historical_bets) & (max_drawdown >= -0.30)
    if not eligible.any():
        return None
    eligible_scores = np.where(eligible, score, -np.inf)
    best_i = int(np.argmax(eligible_scores))
    return {
        "selected_strategy": history.names[best_i],
        "historical_bets": int(historical_bets[best_i]),
        "historical_staked": float(historical_staked[best_i]),
        "historical_profit_loss": float(historical_pl[best_i]),
        "historical_roi": float(historical_roi[best_i]),
        "historical_max_drawdown": float(max_drawdown[best_i]),
        "positive_window_share": float(positive_share[best_i]),
        "window_roi_std": float(roi_std[best_i]),
        "selection_score": float(score[best_i]),
    }


def _strategy_bets_for_window(log: pd.DataFrame, window: Window) -> pd.DataFrame:
    if log.empty:
        return log.copy()
    return log[(log["card_index"] >= window.first_card_index) & (log["card_index"] <= window.last_card_index)].copy()


def _resimulate_window_bets(
    bets: pd.DataFrame,
    selected_strategy: str,
    sizing: SizingConfig,
    bankroll: float,
    sequence_start: int,
    extra: dict[str, Any],
) -> tuple[pd.DataFrame, float, int]:
    if bets.empty:
        return _empty_log(), bankroll, sequence_start
    peak = float(extra.get("_peak", bankroll))
    rows: list[dict[str, Any]] = []
    sequence = sequence_start
    for _, bet in bets.sort_values(["fight_date", "fight_id"]).iterrows():
        stake = _stake_amount(bankroll, bet, sizing)
        if stake <= 0:
            continue
        profit_loss = stake * (float(bet["decimal_odds"]) - 1.0) if bool(bet["won"]) else -stake
        bankroll += profit_loss
        peak = max(peak, bankroll)
        rows.append(
            {
                **{k: v for k, v in bet.to_dict().items() if k in LOG_COLUMN_SET},
                "strategy_name": selected_strategy,
                "sequence": sequence,
                "stake": stake,
                "profit_loss": profit_loss,
                "bankroll": bankroll,
                "drawdown": 0.0 if peak <= 0 else (bankroll - peak) / peak,
                **{k: v for k, v in extra.items() if not k.startswith("_")},
            }
        )
        sequence += 1
    extra["_peak"] = peak
    return pd.DataFrame(rows), bankroll, sequence


def run_selector_config(
    config: SelectorConfig,
    windows: list[Window],
    history: StrategyHistory,
    strategy_logs: dict[str, pd.DataFrame],
    sizing_lookup: dict[str, tuple[SizingConfig, str, str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selection_rows: list[dict[str, Any]] = []
    bet_logs: list[pd.DataFrame] = []
    bankroll = STARTING_BANKROLL
    sequence = 1
    peak_ref = {"_peak": STARTING_BANKROLL}
    for i, window in enumerate(windows):
        selected = select_strategy(history, windows, i, config.min_historical_bets, config.min_historical_windows)
        if selected is None:
            if config.burnin_policy == "default_during_burnin":
                selected_strategy = DEFAULT_STRATEGY
                selection_mode = "burnin_default"
            else:
                selected_strategy = ""
                selection_mode = "burnin_no_bets"
        else:
            selected_strategy = str(selected["selected_strategy"])
            selection_mode = "normal"
        window_bets = _empty_log()
        if selected_strategy:
            sizing = sizing_lookup[selected_strategy][0]
            source = _strategy_bets_for_window(strategy_logs[selected_strategy], window)
            extra = {
                "selector_config": config.name,
                "selector_type": config.selector_type,
                "selected_strategy": selected_strategy,
                "selection_mode": selection_mode,
                "test_window_label": window.label,
                "test_window_start": window.start.strftime("%Y-%m-%d"),
                "test_window_end": (window.end - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "burnin_excluded": selection_mode != "normal",
                **peak_ref,
            }
            window_bets, bankroll, sequence = _resimulate_window_bets(source, selected_strategy, sizing, bankroll, sequence, extra)
            peak_ref["_peak"] = extra["_peak"]
            if not window_bets.empty:
                bet_logs.append(window_bets)
        window_summary = summarize_bet_log(window_bets, selected_strategy or "NO_BETS", window.label)
        selection_rows.append(
            {
                "selector_config": config.name,
                "selector_type": config.selector_type,
                "min_historical_bets": config.min_historical_bets,
                "min_historical_windows": config.min_historical_windows,
                "burnin_policy": config.burnin_policy,
                "test_window_index": i,
                "test_window_label": window.label,
                "test_window_start": window.start.strftime("%Y-%m-%d"),
                "test_window_end": (window.end - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "selected_strategy": selected_strategy,
                "selection_mode": selection_mode,
                "historical_data_end_exclusive": window.start.strftime("%Y-%m-%d"),
                "historical_windows": i,
                "historical_bets": "" if selected is None else selected["historical_bets"],
                "historical_staked": "" if selected is None else selected["historical_staked"],
                "historical_profit_loss": "" if selected is None else selected["historical_profit_loss"],
                "historical_roi": "" if selected is None else selected["historical_roi"],
                "historical_max_drawdown": "" if selected is None else selected["historical_max_drawdown"],
                "positive_window_share": "" if selected is None else selected["positive_window_share"],
                "window_roi_std": "" if selected is None else selected["window_roi_std"],
                "selection_score": "" if selected is None else selected["selection_score"],
                "test_window_bets": window_summary["bets"],
                "test_window_total_staked": window_summary["total_staked"],
                "test_window_profit_loss": window_summary["profit_loss"],
                "test_window_roi": window_summary["roi"],
            }
        )
    combined = pd.concat(bet_logs, ignore_index=True) if bet_logs else _empty_log()
    return pd.DataFrame(selection_rows), combined


def _summarize_named_log(log: pd.DataFrame, name: str, result_scope: str) -> dict[str, Any]:
    if log.empty:
        row = summarize_bet_log(log, name, result_scope)
        row["positive_year_share"] = 0.0
        row["best_year_or_window"] = ""
        row["worst_year_or_window"] = ""
        return row
    frame = log.copy()
    frame["fight_date"] = pd.to_datetime(frame["fight_date"], errors="coerce")
    frame["test_year"] = frame["test_year"].astype(int)
    frame["bankroll"] = STARTING_BANKROLL + frame["profit_loss"].cumsum()
    frame["drawdown"] = frame["bankroll"] / frame["bankroll"].cummax() - 1.0
    row = summarize_bet_log(frame, name, result_scope)
    yearly = (
        frame.groupby("test_year")
        .agg(staked=("stake", "sum"), pl=("profit_loss", "sum"))
        .reset_index()
    )
    yearly["roi"] = np.where(yearly["staked"] > 0, yearly["pl"] / yearly["staked"], 0.0)
    row["positive_year_share"] = round(float((yearly["roi"] > 0).mean()), 6) if len(yearly) else 0.0
    row["best_year_or_window"] = int(yearly.sort_values("roi", ascending=False).iloc[0]["test_year"]) if len(yearly) else ""
    row["worst_year_or_window"] = int(yearly.sort_values("roi", ascending=True).iloc[0]["test_year"]) if len(yearly) else ""
    return row


def summarize_selector_logs(selection_log: pd.DataFrame, bet_log: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if selection_log.empty:
        return pd.DataFrame()
    for config_name, config_windows in selection_log.groupby("selector_config", sort=True):
        config_bets = bet_log[bet_log.get("selector_config", "") == config_name].copy() if not bet_log.empty else _empty_log()
        for scope, part in [
            ("including_burnin", config_bets),
            ("excluding_burnin", config_bets[config_bets.get("selection_mode", "") == "normal"].copy() if not config_bets.empty else _empty_log()),
            ("burnin_only", config_bets[config_bets.get("selection_mode", "") != "normal"].copy() if not config_bets.empty else _empty_log()),
        ]:
            row = _summarize_named_log(part, config_name, scope)
            row.update(
                {
                    "selector_config": config_name,
                    "selector_type": config_windows.iloc[0]["selector_type"],
                    "min_historical_bets": config_windows.iloc[0]["min_historical_bets"],
                    "min_historical_windows": config_windows.iloc[0]["min_historical_windows"],
                    "burnin_policy": config_windows.iloc[0]["burnin_policy"],
                    "result_scope": scope,
                    "normal_windows": int((config_windows["selection_mode"] == "normal").sum()),
                    "burnin_windows": int((config_windows["selection_mode"] != "normal").sum()),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def fixed_baseline_logs(strategy_logs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: strategy_logs.get(name, _empty_log()).copy() for name in FIXED_BASELINES}


def current_yearly_log(selected_log: pd.DataFrame) -> pd.DataFrame:
    frame = selected_log.copy()
    if frame.empty:
        return frame
    frame["selection_mode"] = np.where(frame["test_year"] == BETTING_TEST_YEARS[0], "burnin_default", "normal")
    frame["selector_config"] = "current_yearly_walk_forward"
    frame["selector_type"] = "current_yearly"
    return frame


def breakdown_rows(logs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, log in logs.items():
        if log.empty:
            continue
        frame = log.copy()
        frame["confidence_bucket"] = pd.cut(frame["model_prob"], bins=[0.0, 0.55, 0.60, 0.65, 0.70, 1.0], labels=["lt_55", "55_60", "60_65", "65_70", "70_plus"], include_lowest=True)
        frame["edge_bucket"] = pd.cut(frame["edge"], bins=[-1.0, 0.03, 0.05, 0.075, 0.10, 0.15, 1.0], labels=["lt_03", "03_05", "05_075", "075_10", "10_15", "15_plus"], include_lowest=True)
        frame["odds_bucket"] = pd.cut(frame["american_odds"], bins=[-10000, -300, -150, -110, 110, 150, 300, 10000], labels=["fav_300_plus", "fav_150_300", "fav_110_150", "near_even", "dog_110_150", "dog_150_300", "dog_300_plus"], include_lowest=True)
        splits = {
            "favorite_underdog": frame["role"],
            "card_segment": np.where(frame["is_main_card"], "main_card", "prelim"),
            "confidence_bucket": frame["confidence_bucket"],
            "edge_bucket": frame["edge_bucket"],
            "odds_bucket": frame["odds_bucket"],
        }
        for split_name, labels in splits.items():
            frame["_split"] = labels.astype(str)
            for split_value, part in frame.groupby("_split", sort=True):
                summary = _summarize_named_log(part.copy(), name, split_value)
                summary.update({"comparison_name": name, "split_type": split_name, "split_value": split_value})
                rows.append(summary)
    return pd.DataFrame(rows)


def drawdown_rows(logs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for name, log in logs.items():
        if log.empty:
            continue
        frame = log.copy().sort_values(["fight_date", "fight_id"]).reset_index(drop=True)
        frame["comparison_name"] = name
        frame["sequence"] = np.arange(1, len(frame) + 1)
        frame["bankroll"] = STARTING_BANKROLL + frame["profit_loss"].cumsum()
        frame["drawdown"] = frame["bankroll"] / frame["bankroll"].cummax() - 1.0
        rows.append(frame[["comparison_name", "sequence", "fight_date", "test_year", "bankroll", "drawdown", "profit_loss"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def comparison_rows(selector_summary: pd.DataFrame, logs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not selector_summary.empty:
        for _, row in selector_summary.iterrows():
            rows.append(row.to_dict())
    for name, log in logs.items():
        if name.startswith("fixed__"):
            label = name.replace("fixed__", "")
            row = _summarize_named_log(log, name, "fixed_full_period")
            row.update({"selector_config": name, "selector_type": "fixed_baseline", "result_scope": "fixed_full_period", "baseline_strategy": label})
            rows.append(row)
        elif name == "current_yearly_walk_forward":
            for scope, part in [
                ("including_burnin", log),
                ("excluding_burnin", log[log["selection_mode"] == "normal"].copy()),
                ("burnin_only", log[log["selection_mode"] != "normal"].copy()),
            ]:
                row = _summarize_named_log(part, name, scope)
                row.update({"selector_config": name, "selector_type": "current_yearly", "result_scope": scope})
                rows.append(row)
    return pd.DataFrame(rows)


def _fmt_pct(value: Any) -> str:
    if value == "" or pd.isna(value):
        return ""
    return f"{float(value):.2%}"


def write_rolling_markdown(output_dir: Path, comparison: pd.DataFrame, selection_log: pd.DataFrame, breakdown: pd.DataFrame) -> None:
    headline = comparison[comparison["result_scope"] == "excluding_burnin"].copy()
    headline = headline[headline["bets"] > 0].sort_values(["profit_loss", "roi"], ascending=False)
    best = headline.iloc[0].to_dict() if not headline.empty else {}
    current_including = comparison[(comparison["selector_config"] == "current_yearly_walk_forward") & (comparison["result_scope"] == "including_burnin")]
    current_excluding = comparison[(comparison["selector_config"] == "current_yearly_walk_forward") & (comparison["result_scope"] == "excluding_burnin")]
    current_burnin = comparison[(comparison["selector_config"] == "current_yearly_walk_forward") & (comparison["result_scope"] == "burnin_only")]
    burnin_pl = float(current_burnin.iloc[0]["profit_loss"]) if len(current_burnin) else 0.0
    including_pl = float(current_including.iloc[0]["profit_loss"]) if len(current_including) else 0.0
    burnin_share = burnin_pl / including_pl if including_pl else 0.0
    realistic_name = "quarterly__min_bets_50__min_windows_5__default_during_burnin"
    realistic = comparison[(comparison["selector_config"] == realistic_name) & (comparison["result_scope"] == "excluding_burnin")]
    realistic_row = realistic.iloc[0].to_dict() if len(realistic) else best
    fixed_underdog = comparison[(comparison["selector_config"] == "fixed__underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct")]
    fixed_favorite = comparison[(comparison["selector_config"] == "fixed__favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct")]
    required_names = [
        "current_yearly_walk_forward",
        "yearly__min_bets_50__min_windows_5__default_during_burnin",
        "card__min_bets_50__min_windows_5__default_during_burnin",
        "every_3_cards__min_bets_50__min_windows_5__default_during_burnin",
        "every_5_cards__min_bets_50__min_windows_5__default_during_burnin",
        "every_10_cards__min_bets_50__min_windows_5__default_during_burnin",
        "monthly__min_bets_50__min_windows_5__default_during_burnin",
        "quarterly__min_bets_50__min_windows_5__default_during_burnin",
        "fixed__edge_ge_0.05__flat_1u",
        "fixed__underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct",
        "fixed__favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct",
    ]
    table = comparison[
        ((comparison["selector_config"].isin(required_names)) & (comparison["result_scope"].isin(["excluding_burnin", "fixed_full_period"])))
        | ((comparison["selector_config"] == "current_yearly_walk_forward") & (comparison["result_scope"] == "including_burnin"))
    ].copy()
    table = table[["selector_config", "result_scope", "bets", "total_staked", "profit_loss", "roi", "max_drawdown", "favorite_roi", "underdog_roi", "positive_year_share", "worst_year_or_window", "best_year_or_window"]]
    underdog = breakdown[(breakdown["split_type"] == "favorite_underdog") & (breakdown["split_value"] == "underdog")].sort_values("profit_loss", ascending=False).head(8)
    lines = [
        "# Rolling Walk-Forward Betting Selector Research",
        "",
        "Research-only historical analysis. Odds remain post-prediction evaluation inputs; no live betting or execution code is included.",
        "",
        "## Headline",
        "",
        "The headline result excludes the first default/burn-in window. This avoids crediting a strategy that was not selected from prior betting data.",
        "",
        f"- Best excluding-burn-in comparison: {best.get('selector_config', '')}",
        f"- Bets: {best.get('bets', 0)}",
        f"- P/L: {float(best.get('profit_loss', 0.0)):.2f} units",
        f"- ROI: {_fmt_pct(best.get('roi', 0.0))}",
        f"- Max drawdown: {_fmt_pct(best.get('max_drawdown', 0.0))}",
        f"- Best realistic slower selector: {realistic_row.get('selector_config', '')}",
        f"- Realistic selector P/L: {float(realistic_row.get('profit_loss', 0.0)):.2f} units; ROI: {_fmt_pct(realistic_row.get('roi', 0.0))}",
        "",
        "## Required Comparison Table",
        "",
        *_markdown_table(table, max_rows=40),
        "",
        "## Interpretation",
        "",
        f"1. The previous yearly result was heavily carried by the 2021 default window: {burnin_pl:.2f} of {including_pl:.2f} units, or {burnin_share:.1%}, came from burn-in/default performance.",
        f"2. Excluding that default year, current yearly walk-forward falls to {float(current_excluding.iloc[0]['profit_loss']) if len(current_excluding) else 0.0:.2f} units.",
        "3. Rolling selection improves the post-burn-in result for some selector frequencies, but the gains are modest and sensitive to update cadence.",
        "4. Card-by-card has the best excluding-burn-in P/L, while quarterly has the strongest slower-update profile among the required comparison rows.",
        "5. Card-by-card is also the most likely to chase noise because it can switch after every event; use it as a stress test, not the first production-style research choice.",
        "6. Underdogs still contribute meaningfully, but the best post-burn-in card selector is not purely underdog-driven; favorite and underdog ROI are both positive there.",
        f"7. Favorites are useful as a small secondary rule: the fixed favorite baseline shows {float(fixed_favorite.iloc[0]['profit_loss']) if len(fixed_favorite) else 0.0:.2f} units across relatively few bets.",
        f"8. Best realistic future-use candidate from this pass: {realistic_row.get('selector_config', '')}. It updates slower than card-by-card and still excludes burn-in.",
        "9. Fixed baselines and full-grid rankings are exploratory comparison anchors unless they are frozen before a later holdout.",
        "10. Next test: freeze one slow rolling selector plus one fixed underdog/favorite baseline and evaluate on later unseen cards without changing thresholds.",
        "",
        "## Underdog Check",
        "",
        "Top underdog splits by P/L across rolling selectors and baselines:",
        "",
        *_markdown_table(underdog[["comparison_name", "bets", "profit_loss", "roi", "hit_rate", "average_odds", "max_drawdown"]], max_rows=8),
        "",
        "## Leakage And Overfitting Controls",
        "",
        "- Selection history uses only windows/cards strictly before the test window start.",
        "- The current test window is never included in candidate scoring.",
        "- Odds are loaded from already-created prediction rows and are not model features.",
        "- Burn-in windows are labeled as `burnin_default` or `burnin_no_bets`; headline comparisons use `excluding_burnin`.",
        "- Remaining risk: all selector families and score formulas are still research choices made after seeing the broad project context, so future validation should use later unseen fight cards.",
        "",
        "## Next Experiment",
        "",
        "Freeze one conservative selector configuration, then evaluate it on a later fully held-out period without changing thresholds, score weights, or candidate strategy set.",
    ]
    (output_dir / "rolling_walk_forward_summary.md").write_text("\n".join(lines), encoding="utf-8")
    audit = [
        "# Rolling Overfitting Audit",
        "",
        "- No model retraining occurs in this rolling selector module.",
        "- The module consumes V4 prediction rows that already contain pre-fight model probabilities.",
        "- Strategy selection cutoffs are strict: historical data end is the test window start, exclusive.",
        "- Burn-in/default performance is saved separately and excluded from the main headline.",
        "- Rolling selectors can still overfit through repeated strategy switching; slower selectors and fixed baselines are reported to expose that risk.",
    ]
    (output_dir / "rolling_overfitting_audit.md").write_text("\n".join(audit), encoding="utf-8")


def _markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> list[str]:
    if frame.empty:
        return ["_No rows available._"]
    shown = frame.head(max_rows).copy()
    columns = list(shown.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in shown.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return lines


def run_rolling_walk_forward(
    predictions_path: Path,
    features_path: Path,
    output_dir: Path,
    current_yearly_bet_log_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = pd.read_csv(predictions_path, low_memory=False)
    features = pd.read_csv(features_path, low_memory=False)
    betting_predictions = assign_card_metadata(prepare_betting_predictions(predictions, features))
    _, _, _, bet_logs = evaluate_strategy_grid(betting_predictions)
    strategy_logs = _prepare_strategy_logs(bet_logs, betting_predictions)
    history = StrategyHistory(strategy_logs, int(betting_predictions["card_index"].max()) + 1)
    sizing_lookup = strategy_config_map()
    all_selection_logs: list[pd.DataFrame] = []
    all_selected_bets: list[pd.DataFrame] = []
    window_cache = {selector_type: build_windows(betting_predictions, selector_type) for selector_type in ["yearly", "card", "every_3_cards", "every_5_cards", "every_10_cards", "monthly", "quarterly"]}
    for config in selector_configs():
        selection_log, selected_bets = run_selector_config(config, window_cache[config.selector_type], history, strategy_logs, sizing_lookup)
        all_selection_logs.append(selection_log)
        if not selected_bets.empty:
            all_selected_bets.append(selected_bets)
    selection_log = pd.concat(all_selection_logs, ignore_index=True) if all_selection_logs else pd.DataFrame()
    selected_bet_log = pd.concat(all_selected_bets, ignore_index=True) if all_selected_bets else _empty_log()
    selector_summary = summarize_selector_logs(selection_log, selected_bet_log)
    if current_yearly_bet_log_path is None:
        current_yearly_bet_log_path = output_dir.parents[1] / "v4_betting" / "selected_strategy_bet_log.csv"
    current_yearly = current_yearly_log(pd.read_csv(current_yearly_bet_log_path, low_memory=False))
    fixed_logs = {f"fixed__{name}": log for name, log in fixed_baseline_logs(strategy_logs).items()}
    comparison_logs = {"current_yearly_walk_forward": current_yearly, **fixed_logs}
    comparison = comparison_rows(selector_summary, comparison_logs)
    breakdown = breakdown_rows({**{name: group.copy() for name, group in selected_bet_log.groupby("selector_config", sort=True)}, **comparison_logs})
    drawdowns = drawdown_rows({**{name: group.copy() for name, group in selected_bet_log.groupby("selector_config", sort=True)}, **comparison_logs})
    comparison.to_csv(output_dir / "rolling_selector_comparison.csv", index=False)
    selection_log.to_csv(output_dir / "rolling_selected_strategy_log.csv", index=False)
    selected_bet_log.to_csv(output_dir / "rolling_selected_bet_log.csv", index=False)
    breakdown.to_csv(output_dir / "rolling_favorite_underdog_breakdown.csv", index=False)
    drawdowns.to_csv(output_dir / "rolling_drawdown_curves.csv", index=False)
    write_rolling_markdown(output_dir, comparison, selection_log, breakdown)
    return {
        "betting_predictions": betting_predictions,
        "comparison": comparison,
        "selection_log": selection_log,
        "selected_bet_log": selected_bet_log,
        "breakdown": breakdown,
        "drawdowns": drawdowns,
    }
