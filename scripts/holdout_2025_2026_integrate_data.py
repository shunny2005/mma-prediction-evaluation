#!/usr/bin/env python3
"""Convert the user-supplied 2025-2026 box-score dataset into the repo's canonical
fight schema and stage it as a `data/updates/ufcstats_*.csv` patch file.

Provenance: the box-score file was supplied by the user, reconstructed from the public
`Greco1899/scrape_ufc_stats` UFCStats mirror -- NOT scraped directly from ufcstats.com by
this session. That provenance is preserved in the `source_dataset` column on every
converted row and documented in holdout-2025-2026/DATA_AUDIT.md.

This script ONLY converts and stages the patch file (data/updates/ufcstats_box_scores_
2025-01-11_through_2026-03-28.csv). It does NOT modify canonical_fights.csv itself --
that file is rebuilt from scratch, from the V3 raw source plus every data/updates/*.csv
patch (this one included), by scripts/holdout_2025_2026_rebuild_state.py, which also
writes the full DATA_AUDIT.md. Run that script after this one.

Reproduce: PYTHONPATH=src .venv/bin/python scripts/holdout_2025_2026_integrate_data.py
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from mma_v4.core import clean_division, fight_weight_from_division, fighter_id
from mma_v4.paths import DATA_DIR, PROJECT_ROOT

RAW_BOX_SCORES = PROJECT_ROOT / "ufcstats_box_scores_2025-01-01_through_2026-04-03.csv"
REPLACE_START = "2025-01-11"
REPLACE_END = "2026-03-28"
STAGED_OUTPUT = DATA_DIR / "updates" / f"ufcstats_box_scores_{REPLACE_START}_through_{REPLACE_END}.csv"


def parse_scheduled_rounds(time_format: str) -> float:
    match = re.match(r"\s*(\d+)\s+Rnd", str(time_format) or "")
    return float(match.group(1)) if match else np.nan


def convert_row(row: pd.Series) -> dict:
    a_name, b_name = row["fighter_a"], row["fighter_b"]
    winner = row["winner"] if pd.notna(row["winner"]) else ""
    loser = row["loser"] if pd.notna(row["loser"]) else ""
    result_map = {"win": "Win", "draw": "Draw", "no_contest": "No Contest"}
    result = result_map.get(str(row["result_type"]).strip().lower(), "Unknown")
    result_a_win = 1.0 if winner == a_name else 0.0 if winner == b_name else np.nan
    division = clean_division(row["weight_class"])
    fight_weight_lbs, fight_weight_source, fight_weight_is_imputed = fight_weight_from_division(row["weight_class"])
    fight_url_id = str(row["fight_url"]).rstrip("/").split("/")[-1]
    event_url_id = str(row["event_url"]).rstrip("/").split("/")[-1]

    def f(col_a: str, col_b: str) -> tuple[float, float]:
        return (pd.to_numeric(row.get(col_a), errors="coerce"), pd.to_numeric(row.get(col_b), errors="coerce"))

    sig_l, sig_l_b = f("a_sig_str_landed", "b_sig_str_landed")
    sig_a, sig_a_b = f("a_sig_str_attempted", "b_sig_str_attempted")
    tot_l, tot_l_b = f("a_total_str_landed", "b_total_str_landed")
    tot_a, tot_a_b = f("a_total_str_attempted", "b_total_str_attempted")
    td_l, td_l_b = f("a_td_landed", "b_td_landed")
    td_a, td_a_b = f("a_td_attempted", "b_td_attempted")
    sub_a, sub_b = f("a_sub_att", "b_sub_att")
    rev_a, rev_b = f("a_rev", "b_rev")
    ctrl_a, ctrl_b = f("a_ctrl_sec", "b_ctrl_sec")
    dist_l_a, dist_l_b = f("a_distance_landed", "b_distance_landed")
    dist_a_a, dist_a_b = f("a_distance_attempted", "b_distance_attempted")
    clinch_l_a, clinch_l_b = f("a_clinch_landed", "b_clinch_landed")
    clinch_a_a, clinch_a_b = f("a_clinch_attempted", "b_clinch_attempted")
    ground_l_a, ground_l_b = f("a_ground_landed", "b_ground_landed")
    ground_a_a, ground_a_b = f("a_ground_attempted", "b_ground_attempted")
    kd_a, kd_b = f("a_kd", "b_kd")

    round_number = pd.to_numeric(row.get("end_round"), errors="coerce")
    fight_time_seconds = np.nan
    end_time = str(row.get("end_time") or "")
    m = re.match(r"\s*(\d+):(\d+)\s*", end_time)
    if m and pd.notna(round_number):
        fight_time_seconds = (round_number - 1) * 300 + int(m.group(1)) * 60 + int(m.group(2))

    return {
        "fight_id": f"ufcstats_{fight_url_id}",
        "event_id": f"ufcstats_{event_url_id}",
        "event_name": row["event"],
        "fight_date": pd.to_datetime(row["event_date"]).date().isoformat(),
        "weight_class": division,
        "fighter_a_id": fighter_id(a_name),
        "fighter_a_name": a_name,
        "fighter_b_id": fighter_id(b_name),
        "fighter_b_name": b_name,
        "winner_name": winner,
        "loser_name": loser,
        "result": result,
        "method": row.get("method", ""),
        "round": round_number,
        "time": end_time,
        "scheduled_rounds": parse_scheduled_rounds(row.get("time_format")),
        "fighter_a_age": np.nan,
        "fighter_b_age": np.nan,
        "fighter_a_height": np.nan,
        "fighter_b_height": np.nan,
        "fighter_a_reach": np.nan,
        "fighter_b_reach": np.nan,
        "fighter_a_stance": "",
        "fighter_b_stance": "",
        "fighter_a_sig_str_landed": sig_l,
        "fighter_a_sig_str_attempted": sig_a,
        "fighter_b_sig_str_landed": sig_l_b,
        "fighter_b_sig_str_attempted": sig_a_b,
        "fighter_a_total_str_landed": tot_l,
        "fighter_a_total_str_attempted": tot_a,
        "fighter_b_total_str_landed": tot_l_b,
        "fighter_b_total_str_attempted": tot_a_b,
        "fighter_a_td_landed": td_l,
        "fighter_a_td_attempted": td_a,
        "fighter_b_td_landed": td_l_b,
        "fighter_b_td_attempted": td_a_b,
        "fighter_a_sub_attempts": sub_a,
        "fighter_b_sub_attempts": sub_b,
        "fighter_a_reversals": rev_a,
        "fighter_b_reversals": rev_b,
        "fighter_a_control_time_seconds": ctrl_a,
        "fighter_b_control_time_seconds": ctrl_b,
        "source_file": row["event_url"],
        "source_dataset": "ufcstats.com (via Greco1899/scrape_ufc_stats mirror, user-supplied)",
        "source_quality_score": 1.0,
        "result_a_win": result_a_win,
        "fight_time_seconds": fight_time_seconds,
        "fighter_a_distance_str_landed": dist_l_a,
        "fighter_a_distance_str_attempts": dist_a_a,
        "fighter_b_distance_str_landed": dist_l_b,
        "fighter_b_distance_str_attempts": dist_a_b,
        "fighter_a_clinch_str_landed": clinch_l_a,
        "fighter_a_clinch_str_attempts": clinch_a_a,
        "fighter_b_clinch_str_landed": clinch_l_b,
        "fighter_b_clinch_str_attempts": clinch_a_b,
        "fighter_a_ground_str_landed": ground_l_a,
        "fighter_a_ground_str_attempts": ground_a_a,
        "fighter_b_ground_str_landed": ground_l_b,
        "fighter_b_ground_str_attempts": ground_a_b,
        "fighter_a_knockdowns": kd_a,
        "fighter_b_knockdowns": kd_b,
        "fight_division": division,
        "division": division,
        "fight_weight_lbs": fight_weight_lbs,
        "fight_weight_source": fight_weight_source,
        "fight_weight_is_imputed": fight_weight_is_imputed,
    }


def main() -> None:
    raw = pd.read_csv(RAW_BOX_SCORES, low_memory=False)
    print(f"Loaded {len(raw)} raw box-score rows across {raw['event'].nunique()} events "
          f"({raw['event_date'].min()} to {raw['event_date'].max()})")

    converted = pd.DataFrame([convert_row(r) for _, r in raw.iterrows()])
    if converted["fight_id"].duplicated().any():
        raise RuntimeError("Duplicate fight_id within the converted box-score file itself.")

    STAGED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    converted.to_csv(STAGED_OUTPUT, index=False)
    print(f"Wrote staged canonical-schema file: {STAGED_OUTPUT} ({len(converted)} rows)")
    print("Next: run scripts/holdout_2025_2026_rebuild_state.py to rebuild canonical_fights.csv "
          "and all downstream fighter-state/feature artifacts from scratch.")


if __name__ == "__main__":
    main()
