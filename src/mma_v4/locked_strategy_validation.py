from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from mma_v4.betting import (
    bets_for_rule,
    prepare_betting_predictions,
    simulate_bets,
    sizing_rules,
    strategy_rules,
)
from mma_v4.rolling_betting import (
    _side_candidates,
    _summarize_named_log,
    assign_card_metadata,
)


LOCKED_PRIMARY_SELECTOR = "quarterly__min_bets_50__min_windows_5__default_during_burnin"
LOCKED_PRIMARY_LABEL = "locked_quarterly_selector"
LOCKED_BENCHMARKS = [
    "confidence_ge_0.6__shrunk_kelly_s0.5_k0.25_cap_0.5pct",
    "underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct",
    "favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct",
    "edge_ge_0.05__flat_1u",
]


def _strategy_lookup() -> dict[str, tuple[Any, Any]]:
    lookup: dict[str, tuple[Any, Any]] = {}
    for rule in strategy_rules():
        for sizing in sizing_rules():
            lookup[f"{rule.name}__{sizing.name}"] = (rule, sizing)
    return lookup


def _benchmark_logs(betting_predictions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    sides = _side_candidates(betting_predictions)
    lookup = _strategy_lookup()
    logs: dict[str, pd.DataFrame] = {}
    for strategy_name in LOCKED_BENCHMARKS:
        rule, sizing = lookup[strategy_name]
        bets = bets_for_rule(sides, rule)
        log, _ = simulate_bets(bets, sizing, strategy_name=strategy_name)
        if not log.empty:
            log["fight_date"] = pd.to_datetime(log["fight_date"], errors="coerce")
            log["comparison_name"] = f"fixed__{strategy_name}"
            log["selected_strategy"] = strategy_name
            log["selection_mode"] = "fixed_baseline"
            log["burnin_excluded"] = False
            log["result_scope"] = "fixed_full_period"
            log["card_event"] = log["fight_date"].dt.strftime("%Y-%m-%d")
        logs[f"fixed__{strategy_name}"] = log
    return logs


def _locked_selector_log(rolling_selected_bet_log: pd.DataFrame) -> pd.DataFrame:
    frame = rolling_selected_bet_log[rolling_selected_bet_log["selector_config"] == LOCKED_PRIMARY_SELECTOR].copy()
    if frame.empty:
        return frame
    frame["fight_date"] = pd.to_datetime(frame["fight_date"], errors="coerce")
    frame["comparison_name"] = LOCKED_PRIMARY_LABEL
    frame["result_scope"] = frame["selection_mode"].map(lambda mode: "excluding_burnin" if mode == "normal" else "burnin_only")
    frame["card_event"] = frame.get("test_window_label", frame["fight_date"].dt.strftime("%Y-%m-%d"))
    return frame


def _results_rows(locked_log: pd.DataFrame, benchmark_logs: dict[str, pd.DataFrame], rolling_comparison: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    locked_rows = rolling_comparison[rolling_comparison["selector_config"] == LOCKED_PRIMARY_SELECTOR].copy()
    for _, row in locked_rows.iterrows():
        out = row.to_dict()
        out["comparison_name"] = LOCKED_PRIMARY_LABEL
        out["strategy_name"] = LOCKED_PRIMARY_SELECTOR
        rows.append(out)
    for comparison_name, log in benchmark_logs.items():
        row = _summarize_named_log(log, comparison_name, "fixed_full_period")
        row["comparison_name"] = comparison_name
        row["strategy_name"] = comparison_name.replace("fixed__", "")
        row["selector_config"] = comparison_name
        row["selector_type"] = "fixed_benchmark"
        row["result_scope"] = "fixed_full_period"
        rows.append(row)
    preferred = [
        "comparison_name",
        "strategy_name",
        "result_scope",
        "bets",
        "wins",
        "losses",
        "hit_rate",
        "total_staked",
        "profit_loss",
        "roi",
        "ending_bankroll",
        "max_drawdown",
        "favorite_roi",
        "underdog_roi",
        "main_card_roi",
        "positive_year_share",
        "best_year_or_window",
        "worst_year_or_window",
        "favorite_bets",
        "underdog_bets",
        "main_card_bets",
    ]
    result = pd.DataFrame(rows)
    return result[[col for col in preferred if col in result.columns] + [col for col in result.columns if col not in preferred]]


def _locked_bet_log(locked_log: pd.DataFrame, benchmark_logs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    logs = []
    if not locked_log.empty:
        logs.append(locked_log)
    logs.extend(log for log in benchmark_logs.values() if not log.empty)
    if not logs:
        return pd.DataFrame()
    frame = pd.concat(logs, ignore_index=True, sort=False)
    frame["burnin_flag"] = frame.get("selection_mode", "").isin(["burnin_default", "burnin_no_bets"])
    frame["implied_probability"] = frame["market_prob"]
    frame["market_odds"] = frame["american_odds"]
    frame["bet_result"] = frame["won"].map(lambda value: "win" if bool(value) else "loss")
    frame["date"] = pd.to_datetime(frame["fight_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    columns = [
        "comparison_name",
        "strategy_name",
        "selected_strategy",
        "result_scope",
        "selection_mode",
        "burnin_flag",
        "date",
        "card_event",
        "test_year",
        "fighter",
        "opponent",
        "actual_winner",
        "model_prob",
        "market_odds",
        "implied_probability",
        "edge",
        "role",
        "stake",
        "bet_result",
        "profit_loss",
        "bankroll",
        "drawdown",
        "fight_id",
    ]
    return frame[[col for col in columns if col in frame.columns]]


def _fmt_units(value: Any) -> str:
    return f"{float(value):.2f}"


def _fmt_pct(value: Any) -> str:
    return f"{float(value):.2%}"


def _markdown_table(frame: pd.DataFrame) -> list[str]:
    if frame.empty:
        return ["_No rows available._"]
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return lines


def _write_docs(output_dir: Path, results: pd.DataFrame) -> None:
    locked_ex = results[(results["comparison_name"] == LOCKED_PRIMARY_LABEL) & (results["result_scope"] == "excluding_burnin")].iloc[0]
    locked_full = results[(results["comparison_name"] == LOCKED_PRIMARY_LABEL) & (results["result_scope"] == "including_burnin")].iloc[0]
    locked_burnin = results[(results["comparison_name"] == LOCKED_PRIMARY_LABEL) & (results["result_scope"] == "burnin_only")].iloc[0]
    benchmark_table = results[results["comparison_name"].astype(str).str.startswith("fixed__")][
        ["strategy_name", "bets", "profit_loss", "roi", "max_drawdown", "favorite_roi", "underdog_roi"]
    ]
    lines = [
        "# Locked MMA Betting Strategy",
        "",
        "This is the frozen validation specification. Do not use these results to keep tuning thresholds, candidate rules, score weights, selection cadence, or staking settings.",
        "",
        "## Locked Primary Strategy",
        "",
        f"- Primary selector: `{LOCKED_PRIMARY_SELECTOR}`.",
        "- Selection updates quarterly.",
        "- At the start of each quarter, the selector scores candidate betting rules using only data strictly before that quarter.",
        "- Candidate selection requires at least 50 historical bets and at least 5 historical windows.",
        "- Burn-in uses the default rule when needed, but the headline metric is post-burn-in only.",
        "- Headline result scope: `excluding_burnin`.",
        "",
        "Quarterly was chosen instead of card-by-card because it is less reactive and less likely to chase short-term noise, while still retaining the best slower-update historical profile from the rolling experiment.",
        "",
        "## Historical Reference",
        "",
        f"- Locked quarterly excluding burn-in: {int(locked_ex['bets'])} bets, {_fmt_units(locked_ex['profit_loss'])} units P/L, {_fmt_pct(locked_ex['roi'])} ROI, {_fmt_pct(locked_ex['max_drawdown'])} max drawdown.",
        f"- Full period including burn-in: {int(locked_full['bets'])} bets, {_fmt_units(locked_full['profit_loss'])} units P/L, {_fmt_pct(locked_full['roi'])} ROI.",
        f"- Burn-in only: {int(locked_burnin['bets'])} bets, {_fmt_units(locked_burnin['profit_loss'])} units P/L, {_fmt_pct(locked_burnin['roi'])} ROI.",
        "",
        "## Frozen Benchmarks",
        "",
        *_markdown_table(benchmark_table),
        "",
        "## Required Interpretation",
        "",
        "1. Locked strategy: quarterly selector with 50 minimum historical bets, 5 minimum historical windows, and default during burn-in.",
        "2. Quarterly was selected because it is a slower, more realistic cadence than card-by-card and had strong post-burn-in historical performance.",
        "3. Burn-in is excluded from the headline because those bets were not selected from enough prior strategy evidence.",
        f"4. Historical reference carried forward: {_fmt_units(locked_ex['profit_loss'])} units P/L, {_fmt_pct(locked_ex['roi'])} ROI, and {_fmt_pct(locked_ex['max_drawdown'])} max drawdown after burn-in.",
        "5. Fixed benchmarks tracked: confidence shrunk Kelly, capped underdog, favorite edge, and edge >= 0.05 flat 1u.",
        "6. Future success: positive post-lock ROI after a meaningful bet count, controlled drawdown ideally under 10%, no dependence on one outlier win, and competitive results versus fixed baselines.",
        "7. Future failure: negative ROI over a meaningful sample, drawdown materially worse than history, dependence on one outlier, consistent benchmark outperformance, or unstable selected rules.",
        "8. Do not change candidate rules, thresholds, score formula, selection cadence, burn-in policy, minimum bet/window thresholds, sizing rules, favorite/underdog definitions, or edge calculations.",
    ]
    (output_dir / "LOCKED_STRATEGY.md").write_text("\n".join(lines), encoding="utf-8")
    audit = [
        "# Locked Strategy Audit",
        "",
        "- No model retraining occurs in this locked validation workflow.",
        "- The workflow consumes already-created V4 prediction rows with model probabilities.",
        "- Odds are merged only after predictions exist and are used only for evaluation, edge calculation, and payout simulation.",
        "- The locked quarterly selector uses only data strictly before each test quarter for selection.",
        "- Burn-in/default windows are present in the logs but excluded from the headline result.",
        "- Candidate strategy set, thresholds, scoring formula, burn-in rules, minimum bet/window thresholds, sizing rules, favorite/underdog definitions, and edge calculations are frozen.",
        "- Any future tuning should happen only in a separate research branch, not by modifying this locked validation result.",
    ]
    (output_dir / "locked_strategy_audit.md").write_text("\n".join(audit), encoding="utf-8")
    plan = [
        "# Locked Strategy Forward Test Plan",
        "",
        "1. Append future completed fight prediction rows generated by the active V4 model before odds are evaluated.",
        "2. Merge closing or otherwise defined historical odds only after those predictions exist.",
        "3. Run the locked validation workflow without changing selector configuration, benchmark rules, thresholds, score weights, or staking logic.",
        "4. Evaluate headline performance using post-burn-in or post-lock bets only.",
        "5. Compare the locked quarterly selector against the four frozen fixed benchmarks.",
        "6. Treat success as positive ROI over a meaningful number of bets with controlled drawdown, no single-bet dependence, stable favorite/underdog splits, and competitive benchmark performance.",
        "7. Treat failure as negative ROI over a meaningful sample, materially worse drawdown, outlier dependence, repeated benchmark outperformance, or unstable rule switching.",
        "",
        "Do not reinterpret poor forward results by adjusting thresholds in this validation workflow. If new research is needed, create a separate future research branch.",
    ]
    (output_dir / "locked_strategy_forward_test_plan.md").write_text("\n".join(plan), encoding="utf-8")


def run_locked_strategy_validation(
    predictions_path: Path,
    features_path: Path,
    rolling_report_dir: Path,
    output_dir: Path,
) -> dict[str, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_predictions = pd.read_csv(predictions_path, low_memory=False)
    features = pd.read_csv(features_path, low_memory=False)
    betting_predictions = assign_card_metadata(prepare_betting_predictions(raw_predictions, features))
    rolling_comparison = pd.read_csv(rolling_report_dir / "rolling_selector_comparison.csv", low_memory=False)
    rolling_selected_bets = pd.read_csv(rolling_report_dir / "rolling_selected_bet_log.csv", low_memory=False)
    locked_log = _locked_selector_log(rolling_selected_bets)
    benchmark_logs = _benchmark_logs(betting_predictions)
    results = _results_rows(locked_log, benchmark_logs, rolling_comparison)
    bet_log = _locked_bet_log(locked_log, benchmark_logs)
    results.to_csv(output_dir / "locked_strategy_results.csv", index=False)
    bet_log.to_csv(output_dir / "locked_strategy_bet_log.csv", index=False)
    _write_docs(output_dir, results)
    return {
        "betting_predictions": betting_predictions,
        "results": results,
        "bet_log": bet_log,
        "locked_log": locked_log,
    }
