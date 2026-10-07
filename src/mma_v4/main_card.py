from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from mma_v4.core import clean_name, expected_calibration_error, prediction_metrics
from mma_v4.paths import PROJECT_ROOT


MAIN_CARD_SIZE = 5
MAIN_CARD_DEFINITION = "first_5_rows_per_date_from_verified_top_to_bottom_raw_card_order"
MDABBERT_RAW = (
    PROJECT_ROOT.parent
    / "v2"
    / "mma_nn_v2"
    / "data"
    / "raw"
    / "mdabbert__ultimate-ufc-dataset"
    / "ufc-master.csv"
)


@dataclass(frozen=True)
class MainCardAudit:
    source_path: Path
    source_columns: tuple[str, ...]
    event_count: int
    fight_count: int
    main_card_count: int
    limitations: tuple[str, ...]


def pair_key(date: Any, fighter_a: Any, fighter_b: Any) -> tuple[str, str]:
    names = sorted([clean_name(fighter_a), clean_name(fighter_b)])
    return (pd.to_datetime(date, errors="coerce").strftime("%Y-%m-%d"), "||".join(names))


def load_raw_main_card_order(raw_path: Path = MDABBERT_RAW, main_card_size: int = MAIN_CARD_SIZE) -> tuple[pd.DataFrame, MainCardAudit]:
    raw = pd.read_csv(raw_path, low_memory=False)
    required = ["date", "R_fighter", "B_fighter"]
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"Raw main-card source is missing required columns: {missing}")

    cards = raw[required].copy()
    cards["fight_date"] = pd.to_datetime(cards["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    cards = cards.dropna(subset=["fight_date", "R_fighter", "B_fighter"]).reset_index(drop=True)
    cards["main_card_source_position"] = cards.groupby("fight_date").cumcount() + 1
    cards["main_card_event_size"] = cards.groupby("fight_date")["fight_date"].transform("size")
    cards["is_main_card"] = cards["main_card_source_position"] <= main_card_size
    cards["main_card_source"] = raw_path.name
    cards["main_card_definition"] = MAIN_CARD_DEFINITION
    cards["_pair_key"] = cards.apply(lambda row: pair_key(row["fight_date"], row["R_fighter"], row["B_fighter"]), axis=1)
    cards = cards.drop_duplicates("_pair_key", keep="first")
    audit = MainCardAudit(
        source_path=raw_path,
        source_columns=tuple(required),
        event_count=int(cards["fight_date"].nunique()),
        fight_count=int(len(cards)),
        main_card_count=int(cards["is_main_card"].sum()),
        limitations=(
            "The selected raw source has date-level card grouping but no event-name column; UFC data usually has one event per date, but same-date multi-event ambiguity cannot be resolved locally.",
            "Main card is approximated as the first five source rows; rare six-fight main cards are intentionally not expanded without an explicit segment flag.",
            "The source file also contains odds columns, but this classifier reads only date and fighter-name columns plus row order.",
        ),
    )
    return cards, audit


def annotate_main_card(features: pd.DataFrame, raw_path: Path = MDABBERT_RAW, main_card_size: int = MAIN_CARD_SIZE) -> tuple[pd.DataFrame, MainCardAudit]:
    cards, audit = load_raw_main_card_order(raw_path, main_card_size)
    card_lookup = cards.set_index("_pair_key")[
        ["is_main_card", "main_card_source", "main_card_source_position", "main_card_event_size", "main_card_definition"]
    ]
    annotated = features.copy()
    annotated["_pair_key"] = annotated.apply(lambda row: pair_key(row["fight_date"], row["fighter_a_name"], row["fighter_b_name"]), axis=1)
    annotated = annotated.join(card_lookup, on="_pair_key")
    annotated["is_main_card"] = annotated["is_main_card"].where(annotated["is_main_card"].notna(), False).astype(bool)
    annotated["main_card_source"] = annotated["main_card_source"].fillna("")
    annotated["main_card_definition"] = annotated["main_card_definition"].fillna("")
    annotated = annotated.drop(columns=["_pair_key"])
    return annotated, audit


def safe_float(value: Any) -> float | str:
    if value == "" or pd.isna(value):
        return ""
    return round(float(value), 4)


def consolidated_metrics(predictions: pd.DataFrame, label: str) -> dict[str, Any]:
    if predictions.empty:
        return {"evaluation": label, "prediction_count": 0}
    y = predictions["label_a_win"].to_numpy(dtype=float)
    p = predictions["fighter_a_win_probability"].to_numpy(dtype=float)
    metrics = prediction_metrics(y, p)
    conf = predictions["prediction_confidence"].to_numpy(dtype=float)
    correct = predictions["prediction_correct"].to_numpy(dtype=bool)
    market = predictions[predictions.get("market_odds_available", False) == True] if "market_odds_available" in predictions else predictions.iloc[0:0]
    model_fav = market[market["model_market_role"] == "model_favorite"] if len(market) else market
    model_dog = market[market["model_market_role"] == "model_underdog"] if len(market) else market
    stress = predictions[predictions["test_year"].isin([2023, 2024])]
    stress_dog = stress[stress.get("model_market_role", "") == "model_underdog"] if "model_market_role" in stress else stress.iloc[0:0]
    return {
        "evaluation": label,
        "prediction_count": int(len(predictions)),
        "accuracy": round(metrics["accuracy"], 4),
        "log_loss": round(metrics["log_loss"], 4),
        "brier_score": round(metrics["brier_score"], 4),
        "ece": round(expected_calibration_error(conf, correct), 4),
        "model_favorite_accuracy": safe_float(model_fav["prediction_correct"].mean()) if len(model_fav) else "",
        "model_underdog_accuracy": safe_float(model_dog["prediction_correct"].mean()) if len(model_dog) else "",
        "false_underdog_count": int((~model_dog["prediction_correct"]).sum()) if len(model_dog) else 0,
        "true_underdog_count": int(model_dog["prediction_correct"].sum()) if len(model_dog) else 0,
        "stress_2023_2024_accuracy": safe_float(stress["prediction_correct"].mean()) if len(stress) else "",
        "stress_2023_2024_underdog_accuracy": safe_float(stress_dog["prediction_correct"].mean()) if len(stress_dog) else "",
    }


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> list[str]:
    if frame.empty:
        return ["_No rows available._"]
    shown = frame.head(max_rows).copy()
    cols = list(shown.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in shown.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in cols) + " |")
    return lines


def year_counts(annotated: pd.DataFrame) -> pd.DataFrame:
    frame = annotated.copy()
    frame["test_year"] = pd.to_datetime(frame["fight_date"], errors="coerce").dt.year
    return (
        frame.groupby("test_year", dropna=False)
        .agg(total_fights=("fight_id", "count"), main_card_fights=("is_main_card", "sum"), source_matched=("main_card_source", lambda s: int((s != "").sum())))
        .reset_index()
    )


def audit_feature_safety(columns: list[str]) -> list[str]:
    unsafe_terms = ["winner", "result", "method", "label", "odds", "market", "fight_year", "year", "main_card"]
    return [column for column in columns if any(term in column.lower() for term in unsafe_terms)]
