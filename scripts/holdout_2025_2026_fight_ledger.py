#!/usr/bin/env python3
"""Part 2/19: build the comprehensive per-fight ledger
(data/fight_ledger_2025_2026.csv) and its companion FIGHT_LEDGER.md summary.

Reproduce: PYTHONPATH=src .venv/bin/python scripts/holdout_2025_2026_fight_ledger.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mma_v4.paths import PROJECT_ROOT

OUT = PROJECT_ROOT / "holdout-2025-2026"
VERIFIED_CUTOVER = "2026-04-03"  # last date covered by the user-supplied box-score file


def main() -> None:
    ledger = pd.read_csv(OUT / "data" / "all_predictions.csv", low_memory=False)
    ledger["bout_order"] = ledger.groupby("event_name").cumcount() + 1
    ledger["odds_timing_known"] = False
    ledger["odds_timing_classification"] = "unknown"
    ledger["data_source_provenance"] = np.where(
        pd.to_datetime(ledger["fight_date"]) <= pd.Timestamp(VERIFIED_CUTOVER),
        "ufcstats.com (via Greco1899/scrape_ufc_stats mirror, user-supplied)",
        "ufcstats.com (direct scrape, verified in a prior session)",
    )
    ledger["model_agrees_with_market"] = np.where(
        ledger["market_odds_available"], ledger["predicted_winner"] == ledger["market_favorite"], np.nan
    )

    bet_logs = pd.read_csv(OUT / "data" / "betting_bet_log_fixed_strategies.csv", low_memory=False)
    quarterly = pd.read_csv(OUT / "data" / "locked_quarterly_selector_bet_log.csv", low_memory=False)
    quarterly = quarterly.assign(strategy="locked_quarterly_selector")
    all_bets = pd.concat([bet_logs, quarterly], ignore_index=True, sort=False)

    for strategy_name in sorted(all_bets["strategy"].unique()):
        s = all_bets[all_bets["strategy"] == strategy_name][["fight_id", "fighter", "stake", "won", "profit_loss"]]
        col_prefix = f"bet_{strategy_name}"
        merged = ledger[["fight_id", "fighter_a_name"]].merge(s, on="fight_id", how="left")
        ledger[f"{col_prefix}_placed"] = merged["stake"].notna()
        ledger[f"{col_prefix}_side"] = np.where(merged["fighter"].isna(), "", np.where(merged["fighter"] == merged["fighter_a_name"], "A", "B"))
        ledger[f"{col_prefix}_stake"] = merged["stake"]
        ledger[f"{col_prefix}_result"] = np.where(merged["stake"].isna(), "no_bet", np.where(merged["won"], "win", "loss"))
        ledger[f"{col_prefix}_profit_loss"] = merged["profit_loss"]

    ledger = ledger.sort_values(["fight_date", "event_name", "bout_order"]).reset_index(drop=True)
    ledger.to_csv(OUT / "data" / "fight_ledger_2025_2026.csv", index=False)
    print(f"Wrote fight_ledger_2025_2026.csv with {len(ledger)} rows, {len(ledger.columns)} columns.")

    events = ledger[["event_name", "fight_date"]].drop_duplicates().sort_values("fight_date")
    n_2025 = int((pd.to_datetime(ledger["fight_date"]).dt.year == 2025).sum())
    n_2026 = int((pd.to_datetime(ledger["fight_date"]).dt.year == 2026).sum())
    n_matched = int(ledger["market_odds_available"].sum())
    lines = [
        "# Fight Ledger (2025-2026)",
        "",
        f"Every completed UFC fight from {ledger['fight_date'].min()} through {ledger['fight_date'].max()} "
        f"used in this holdout: **{len(ledger)} fights across {events.shape[0]} events** "
        f"({n_2025} in 2025, {n_2026} in 2026). No scheduled/future fights are included -- this ledger "
        "contains only fights with a completed, known result.",
        "",
        f"- {n_matched} of {len(ledger)} fights ({n_matched/len(ledger)*100:.1f}%) have a matched historical "
        "moneyline odds record; the rest have no usable odds match and are excluded from every "
        "market-comparison and betting metric (but are still included in the model/Elo accuracy numbers).",
        "- Box-score data provenance: fights through 2026-03-28 come from a user-supplied file "
        "reconstructed from the public `Greco1899/scrape_ufc_stats` UFCStats mirror (not scraped "
        "directly from ufcstats.com by this session); fights from 2026-04-04 onward come from a prior "
        "session's direct ufcstats.com scrape, independently verified. See `DATA_AUDIT.md` for the full "
        "reconciliation and corruption-fix accounting.",
        "- Odds timing (opening/closing/snapshot) is **UNKNOWN** -- see `LIMITATIONS.md`. Every betting "
        "number in this deliverable is a historical backtest, not a claim of deployable, real-time "
        "executable ROI.",
        "",
        "## Events",
        "",
        "| date | event | fights |",
        "| --- | --- | ---: |",
    ]
    for _, ev in events.iterrows():
        n = int((ledger["event_name"] == ev["event_name"]).sum())
        lines.append(f"| {ev['fight_date']} | {ev['event_name']} | {n} |")
    (OUT / "FIGHT_LEDGER.md").write_text("\n".join(lines) + "\n")
    print("Wrote FIGHT_LEDGER.md")


if __name__ == "__main__":
    main()
