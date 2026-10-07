#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mma_v4.core import clean_division, fight_weight_from_division, fighter_id
from mma_v4.paths import CANONICAL_FIGHTS, CHRONOLOGICAL_FIGHTS, DATA_DIR, PROJECT_ROOT


DEFAULT_RAW = Path("/private/tmp/ufcstats_2026_post_cutoff_raw.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import verified UFCStats fight results into the V4 chronological data.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--expected-count", type=int, default=210)
    parser.add_argument("--start-date", default="2026-04-04")
    parser.add_argument("--end-date", default="2026-08-08")
    parser.add_argument("--as-of-date", default="2026-08-09")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--backup-dir", type=Path, default=None)
    return parser.parse_args()


def pair(value: str) -> tuple[float, float]:
    match = re.match(r"\s*(\d+)\s+of\s+(\d+)\s*", value or "")
    return (float(match.group(1)), float(match.group(2))) if match else (np.nan, np.nan)


def seconds(value: str) -> float:
    match = re.match(r"\s*(\d+):(\d+)\s*", value or "")
    return float(int(match.group(1)) * 60 + int(match.group(2))) if match else np.nan


def labeled_value(text: str, label: str, next_label: str | None = None) -> str:
    if next_label:
        match = re.search(rf"{re.escape(label)}:\s*(.*?)\s+{re.escape(next_label)}:", text)
    else:
        match = re.search(rf"{re.escape(label)}:\s*(.*)$", text)
    return match.group(1).strip() if match else ""


def ascii_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def matchup_key(date: Any, fighter_a: Any, fighter_b: Any) -> str:
    names = sorted([ascii_key(fighter_a), ascii_key(fighter_b)])
    return f"{pd.Timestamp(date).date().isoformat()}||{names[0]}||{names[1]}"


def convert_item(item: dict[str, Any]) -> dict[str, Any]:
    event = item["event"]
    bout = item["bout"]
    detail = item["detail"]
    fighters = detail["fighters"]
    statuses = detail["statuses"]
    if len(fighters) != 2 or len(statuses) != 2:
        raise ValueError(f"Unexpected fighter/status structure for {bout['fight_url']}")

    total = detail["tables"][0]["rows"][0]
    sig = detail["tables"][2]["rows"][0]
    if len(total) < 10 or len(sig) < 9:
        raise ValueError(f"Incomplete stat tables for {bout['fight_url']}")

    a_name, b_name = fighters[0]["name"], fighters[1]["name"]
    a_status, b_status = statuses[0], statuses[1]
    winner = a_name if a_status == "W" else b_name if b_status == "W" else ""
    loser = b_name if a_status == "W" else a_name if b_status == "W" else ""
    result_a_win = 1.0 if a_status == "W" else 0.0 if b_status == "W" else np.nan
    result = "Win" if winner else "Draw" if "D" in statuses else "No Contest" if "NC" in statuses else "Unknown"

    meta = detail.get("meta", "")
    method = labeled_value(meta, "Method", "Round")
    round_text = labeled_value(meta, "Round", "Time")
    time_text = labeled_value(meta, "Time", "Time format")
    format_text = labeled_value(meta, "Time format", "Referee")
    scheduled_match = re.search(r"(\d+)\s+Rnd", format_text)
    scheduled_rounds = int(scheduled_match.group(1)) if scheduled_match else np.nan
    round_number = int(round_text) if round_text.isdigit() else np.nan
    current_round_seconds = seconds(time_text)
    fight_time_seconds = (round_number - 1) * 300 + current_round_seconds if not pd.isna(round_number) else np.nan

    a_sig_l, a_sig_a = pair(total[2][0])
    b_sig_l, b_sig_a = pair(total[2][1])
    a_total_l, a_total_a = pair(total[4][0])
    b_total_l, b_total_a = pair(total[4][1])
    a_td_l, a_td_a = pair(total[5][0])
    b_td_l, b_td_a = pair(total[5][1])
    a_dist_l, a_dist_a = pair(sig[6][0])
    b_dist_l, b_dist_a = pair(sig[6][1])
    a_clinch_l, a_clinch_a = pair(sig[7][0])
    b_clinch_l, b_clinch_a = pair(sig[7][1])
    a_ground_l, a_ground_a = pair(sig[8][0])
    b_ground_l, b_ground_a = pair(sig[8][1])
    division = clean_division(bout["cells"][6][0])
    fight_weight_lbs, fight_weight_source, fight_weight_is_imputed = fight_weight_from_division(division)

    return {
        "fight_id": f"ufcstats_{bout['fight_url'].rstrip('/').split('/')[-1]}",
        "event_id": f"ufcstats_{event['url'].rstrip('/').split('/')[-1]}",
        "event_name": event["name"],
        "fight_date": pd.to_datetime(event["date"]).date().isoformat(),
        "weight_class": division,
        "fighter_a_id": fighter_id(a_name),
        "fighter_a_name": a_name,
        "fighter_b_id": fighter_id(b_name),
        "fighter_b_name": b_name,
        "winner_name": winner,
        "loser_name": loser,
        "result": result,
        "method": method,
        "round": round_number,
        "time": time_text,
        "scheduled_rounds": scheduled_rounds,
        "fighter_a_age": np.nan,
        "fighter_b_age": np.nan,
        "fighter_a_height": np.nan,
        "fighter_b_height": np.nan,
        "fighter_a_reach": np.nan,
        "fighter_b_reach": np.nan,
        "fighter_a_stance": "",
        "fighter_b_stance": "",
        "fighter_a_sig_str_landed": a_sig_l,
        "fighter_a_sig_str_attempted": a_sig_a,
        "fighter_b_sig_str_landed": b_sig_l,
        "fighter_b_sig_str_attempted": b_sig_a,
        "fighter_a_total_str_landed": a_total_l,
        "fighter_a_total_str_attempted": a_total_a,
        "fighter_b_total_str_landed": b_total_l,
        "fighter_b_total_str_attempted": b_total_a,
        "fighter_a_td_landed": a_td_l,
        "fighter_a_td_attempted": a_td_a,
        "fighter_b_td_landed": b_td_l,
        "fighter_b_td_attempted": b_td_a,
        "fighter_a_sub_attempts": float(total[7][0]),
        "fighter_b_sub_attempts": float(total[7][1]),
        "fighter_a_reversals": float(total[8][0]),
        "fighter_b_reversals": float(total[8][1]),
        "fighter_a_control_time_seconds": seconds(total[9][0]),
        "fighter_b_control_time_seconds": seconds(total[9][1]),
        "source_file": event["url"],
        "source_dataset": "ufcstats.com",
        "source_quality_score": 1.0,
        "result_a_win": result_a_win,
        "fight_time_seconds": fight_time_seconds,
        "fighter_a_distance_str_landed": a_dist_l,
        "fighter_a_distance_str_attempts": a_dist_a,
        "fighter_b_distance_str_landed": b_dist_l,
        "fighter_b_distance_str_attempts": b_dist_a,
        "fighter_a_clinch_str_landed": a_clinch_l,
        "fighter_a_clinch_str_attempts": a_clinch_a,
        "fighter_b_clinch_str_landed": b_clinch_l,
        "fighter_b_clinch_str_attempts": b_clinch_a,
        "fighter_a_ground_str_landed": a_ground_l,
        "fighter_a_ground_str_attempts": a_ground_a,
        "fighter_b_ground_str_landed": b_ground_l,
        "fighter_b_ground_str_attempts": b_ground_a,
        "fighter_a_knockdowns": float(total[1][0]),
        "fighter_b_knockdowns": float(total[1][1]),
        "fight_division": division,
        "division": division,
        "fight_weight_lbs": fight_weight_lbs,
        "fight_weight_source": fight_weight_source,
        "fight_weight_is_imputed": fight_weight_is_imputed,
    }


def verified_windows_from_update_files(update_dir: Path) -> list[tuple[str, str]]:
    """Derive (start_date, end_date) verified-supersession windows from every
    `ufcstats_*.csv` patch filename in `update_dir`. Each patch's covered date range
    is data pulled directly from ufcstats.com and should unconditionally supersede
    any non-ufcstats-sourced row inside it -- see `enforce_verified_window_supersession`.

    This was originally a hardcoded two-window list inside a one-off rebuild script
    (`scripts/holdout_2025_2026_rebuild_state.py`, see holdout-2025-2026/
    DATA_AUDIT.md), which meant the routine update pipeline (`build_v4_fighter_state.py`,
    run on every new event per DATA_UPDATE_RUNBOOK.md) never got the fix and would
    silently reintroduce the corrupted third-party rows it was meant to remove on every
    future run. Deriving windows from the patch files themselves makes the fix a
    permanent, self-updating part of the standard pipeline instead of a one-time patch."""
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2})_through_(\d{4}-\d{2}-\d{2})\.csv$")
    windows: list[tuple[str, str]] = []
    for path in sorted(update_dir.glob("ufcstats_*.csv")):
        match = pattern.search(path.name)
        if match:
            windows.append((match.group(1), match.group(2)))
    return windows


def enforce_verified_window_supersession(fights: pd.DataFrame, windows: list[tuple[str, str]]) -> tuple[pd.DataFrame, int]:
    """Unconditionally drop every non-ufcstats.com-sourced row whose `fight_date` falls
    inside any verified ufcstats.com patch window, regardless of whether it happened to
    exact-match an official row under `merge_official`'s (date, fighter_a, fighter_b)
    key. `merge_official`'s exact-match dedup was found to leave residual unmatched
    placeholder duplicates behind -- name variants, mis-ordered pairs -- inflating some
    event dates to up to 39 rows instead of the real 12-14 (holdout-2025-2026/
    DATA_AUDIT.md). Verified data supersedes its entire covered date range
    unconditionally, not just the rows it happens to pattern-match."""
    out = fights.copy()
    out["fight_date"] = pd.to_datetime(out["fight_date"], errors="coerce")
    is_ufcstats = out["fight_id"].astype(str).str.startswith("ufcstats_")
    drop_mask = pd.Series(False, index=out.index)
    for start, end in windows:
        in_window = (out["fight_date"] >= start) & (out["fight_date"] <= end)
        drop_mask = drop_mask | (in_window & ~is_ufcstats)
    n_dropped = int(drop_mask.sum())
    out = out.loc[~drop_mask].copy()
    out["fight_date"] = out["fight_date"].dt.strftime("%Y-%m-%d")
    return out, n_dropped


def merge_official(existing: pd.DataFrame, official: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    out = existing.copy()
    out["fight_date"] = pd.to_datetime(out["fight_date"], errors="coerce")
    official_dates = pd.to_datetime(official["fight_date"], errors="raise")
    official_keys = {
        matchup_key(date, a, b)
        for date, a, b in zip(official_dates, official["fighter_a_name"], official["fighter_b_name"])
    }
    exact_keys = out.apply(lambda row: matchup_key(row["fight_date"], row["fighter_a_name"], row["fighter_b_name"]), axis=1)
    drop_mask = exact_keys.isin(official_keys)

    official_pair_dates: dict[str, list[pd.Timestamp]] = {}
    for date, a, b in zip(official_dates, official["fighter_a_name"], official["fighter_b_name"]):
        pair_key = "||".join(sorted([ascii_key(a), ascii_key(b)]))
        official_pair_dates.setdefault(pair_key, []).append(pd.Timestamp(date))
    unlabeled = out["winner_name"].fillna("").astype(str).str.strip().eq("") & pd.to_numeric(out["result_a_win"], errors="coerce").isna()
    for idx, row in out[unlabeled & ~drop_mask].iterrows():
        pair_key = "||".join(sorted([ascii_key(row["fighter_a_name"]), ascii_key(row["fighter_b_name"])]))
        if any(abs((row["fight_date"] - date).days) <= 1 for date in official_pair_dates.get(pair_key, [])):
            drop_mask.loc[idx] = True

    official_ids = set(official["fight_id"].astype(str))
    superseded = int((drop_mask & ~out["fight_id"].astype(str).isin(official_ids)).sum())
    out = pd.concat([out.loc[~drop_mask], official], ignore_index=True, sort=False)
    out["fight_date"] = pd.to_datetime(out["fight_date"], errors="raise")
    out = out.sort_values(["fight_date", "event_name", "fight_id"], na_position="last").reset_index(drop=True)
    out["fight_date"] = out["fight_date"].dt.strftime("%Y-%m-%d")
    return out, superseded


def main() -> int:
    args = parse_args()
    update_csv = args.output or DATA_DIR / "updates" / f"ufcstats_{args.start_date}_through_{args.end_date}.csv"
    audit_md = args.audit or DATA_DIR / "updates" / f"UFCSTATS_{args.as_of_date}_UPDATE_AUDIT.md"
    backup_dir = args.backup_dir or DATA_DIR / "archive" / f"pre_{args.as_of_date.replace('-', '_')}_update"
    items = json.loads(args.raw.read_text(encoding="utf-8"))
    official = pd.DataFrame([convert_item(item) for item in items])
    if len(official) != args.expected_count or official["fight_id"].nunique() != args.expected_count:
        raise RuntimeError(
            f"Expected {args.expected_count} unique official bouts, found {len(official)} / "
            f"{official['fight_id'].nunique()} unique."
        )
    if official["fight_date"].min() != args.start_date or official["fight_date"].max() != args.end_date:
        raise RuntimeError(
            f"Official date range {official['fight_date'].min()} through {official['fight_date'].max()} "
            f"does not match {args.start_date} through {args.end_date}."
        )

    update_csv.parent.mkdir(parents=True, exist_ok=True)
    official.to_csv(update_csv, index=False)
    backup_dir.mkdir(parents=True, exist_ok=True)
    for source in [CANONICAL_FIGHTS, CHRONOLOGICAL_FIGHTS]:
        backup = backup_dir / source.name
        if not backup.exists():
            shutil.copy2(source, backup)

    existing = pd.read_csv(CHRONOLOGICAL_FIGHTS, low_memory=False)
    combined, removed = merge_official(existing, official)
    baseline = pd.read_csv(backup_dir / CHRONOLOGICAL_FIGHTS.name, low_memory=False)
    _, initially_superseded = merge_official(baseline, official)
    canonical_columns = list(existing.columns)
    for column in canonical_columns:
        if column not in combined:
            combined[column] = np.nan
    combined = combined[canonical_columns]
    combined.to_csv(CANONICAL_FIGHTS, index=False)
    combined.to_csv(CHRONOLOGICAL_FIGHTS, index=False)

    events = official[["event_id", "event_name", "fight_date"]].drop_duplicates().sort_values("fight_date")
    decisive = int(official["result_a_win"].notna().sum())
    draws = int(official["result"].eq("Draw").sum())
    no_contests = int(official["result"].eq("No Contest").sum())
    lines = [
        f"# UFCStats Update Audit — {args.as_of_date}",
        "",
        f"- Source: [UFCStats completed events](http://ufcstats.com/statistics/events/completed?page=all)",
        f"- Imported events: {len(events)}",
        f"- Imported bouts: {len(official)}",
        f"- Date range: {official['fight_date'].min()} through {official['fight_date'].max()}",
        f"- Decisive results: {decisive}",
        f"- Draws: {draws}",
        f"- No contests: {no_contests}",
        f"- Initially superseded exact/one-day placeholder rows: {initially_superseded}",
        f"- Combined chronological rows: {len(combined)}",
        "- Full totals, significant strikes by position, takedowns, submissions, reversals, control time, knockdowns, method, round, and time were imported.",
        "",
        "| date | event | bouts |",
        "| --- | --- | ---: |",
    ]
    counts = official.groupby(["fight_date", "event_name"], as_index=False).size()
    for row in counts.itertuples(index=False):
        lines.append(f"| {row.fight_date} | {row.event_name} | {row.size} |")
    audit_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Imported {len(official)} bouts across {len(events)} events; removed {removed} superseded placeholders in this run.")
    print(f"Updated {CANONICAL_FIGHTS} and {CHRONOLOGICAL_FIGHTS} ({len(combined)} rows).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
