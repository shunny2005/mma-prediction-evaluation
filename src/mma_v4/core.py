"""Public subset of a private module: shared helpers only. The rest is withheld (see README)."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import numpy as np
import pandas as pd


DIVISION_TO_WEIGHT_LBS = {
    "Women's Strawweight": 115.0,
    "Women's Flyweight": 125.0,
    "Women's Bantamweight": 135.0,
    "Women's Featherweight": 145.0,
    "Strawweight": 115.0,
    "Flyweight": 125.0,
    "Bantamweight": 135.0,
    "Featherweight": 145.0,
    "Lightweight": 155.0,
    "Welterweight": 170.0,
    "Middleweight": 185.0,
    "Light Heavyweight": 205.0,
    "Heavyweight": 265.0,
}


def clean_name(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def fighter_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", clean_name(name).lower()).strip("_")
    return f"fighter_{slug}" if slug else "fighter_unknown"


def clean_division(value: Any) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return "Unknown"
    division = str(value).strip()
    division = division.replace("Women’s", "Women's")
    division = re.sub(r"^UFC\s+", "", division)
    division = re.sub(r"\bInterim\b|\bTitle\b|\bBout\b", "", division, flags=re.I)
    division = " ".join(division.split())
    compact = re.sub(r"[\s_.-]+", "", division.lower())
    aliases = {
        "wstrawweight": "Women's Strawweight",
        "womenstrawweight": "Women's Strawweight",
        "womensstrawweight": "Women's Strawweight",
        "wflyweight": "Women's Flyweight",
        "womenflyweight": "Women's Flyweight",
        "womensflyweight": "Women's Flyweight",
        "wbantamweight": "Women's Bantamweight",
        "womenbantamweight": "Women's Bantamweight",
        "womensbantamweight": "Women's Bantamweight",
        "wfeatherweight": "Women's Featherweight",
        "womenfeatherweight": "Women's Featherweight",
        "womensfeatherweight": "Women's Featherweight",
        "lightheavyweight": "Light Heavyweight",
        "catchweight": "Catch Weight",
        "openweight": "Open Weight",
    }
    if compact.startswith("catchweight"):
        return "Catch Weight"
    if compact.startswith("openweight"):
        return "Open Weight"
    return aliases.get(compact, division or "Unknown")


def fight_weight_from_division(value: Any) -> tuple[float, str, bool]:
    text = "" if pd.isna(value) else str(value)
    division = clean_division(text)
    if division in {"Catch Weight", "Open Weight", "Unknown"}:
        match = re.search(r"(\d{3}(?:\.\d+)?)\s*(?:lb|lbs|pounds)?", text, flags=re.I)
        if match:
            return float(match.group(1)), "explicit_numeric_weight_class", False
        return np.nan, "missing_or_unmapped_weight_class", True
    if division in DIVISION_TO_WEIGHT_LBS:
        return DIVISION_TO_WEIGHT_LBS[division], "division_limit_mapping", False
    return np.nan, "missing_or_unmapped_weight_class", True


def prediction_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    pred = p >= 0.5
    eps = 1e-6
    p = np.clip(p, eps, 1.0 - eps)
    return {
        "accuracy": float((pred == y).mean()) if len(y) else 0.0,
        "log_loss": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()) if len(y) else 0.0,
        "brier_score": float(((p - y) ** 2).mean()) if len(y) else 0.0,
    }


def expected_calibration_error(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    if len(conf) == 0:
        return 0.0
    ece = 0.0
    edges = np.linspace(0.5, 1.0, bins + 1)
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (conf >= low) & (conf < high if high < 1.0 else conf <= high)
        if mask.any():
            ece += float(mask.mean()) * abs(float(correct[mask].mean()) - float(conf[mask].mean()))
    return ece


def merge_local_odds(preds: pd.DataFrame, odds_path: Path | None) -> pd.DataFrame:
    """Join historical odds onto predictions by fighter identity, independent of which
    fighter the odds source or the prediction frame happened to list as corner 1/A.

    The odds source's (fighter_1, fighter_2) column order is not guaranteed to match this
    project's (fighter_a, fighter_b) order (which is just "whichever order the raw results
    scrape listed the corners in"). A naive exact-order merge silently drops any fight where
    the two sources disagree on order, non-randomly shrinking the odds-eligible sample. This
    tries the direct order first, then falls back to the reversed order (swapping which odds
    column maps to fighter_a/fighter_b) for anything still unmatched.
    """
    preds = preds.copy()
    preds = preds.drop(columns=[c for c in ["market_odds_available", "market_favorite", "model_market_role"] if c in preds.columns])
    preds["market_odds_available"] = False
    preds["market_favorite"] = ""
    preds["model_market_role"] = "unknown"
    if odds_path is None or not odds_path.exists():
        return preds
    odds = pd.read_csv(odds_path, low_memory=False)
    keep = [c for c in ["fight_date", "fighter_1", "fighter_2", "market_favorite", "fighter_1_odds", "fighter_2_odds"] if c in odds.columns]
    if not {"fight_date", "fighter_1", "fighter_2", "market_favorite"}.issubset(set(keep)):
        return preds
    forward = odds[keep].rename(columns={"fighter_1": "fighter_a_name", "fighter_2": "fighter_b_name"}).drop_duplicates(
        ["fight_date", "fighter_a_name", "fighter_b_name"]
    )
    rename_reversed = {"fighter_1": "fighter_b_name", "fighter_2": "fighter_a_name"}
    if "fighter_1_odds" in keep and "fighter_2_odds" in keep:
        rename_reversed.update({"fighter_1_odds": "fighter_2_odds", "fighter_2_odds": "fighter_1_odds"})
    reversed_odds = odds[keep].rename(columns=rename_reversed).drop_duplicates(["fight_date", "fighter_a_name", "fighter_b_name"])

    base = preds.drop(columns=["market_favorite"]).reset_index(drop=True)
    merged = base.merge(forward, on=["fight_date", "fighter_a_name", "fighter_b_name"], how="left")
    unmatched = merged["market_favorite"].isna()
    if unmatched.any():
        fallback = base.loc[unmatched.to_numpy()].merge(reversed_odds, on=["fight_date", "fighter_a_name", "fighter_b_name"], how="left")
        for column in [c for c in forward.columns if c not in ("fight_date", "fighter_a_name", "fighter_b_name")]:
            merged.loc[unmatched, column] = fallback[column].to_numpy()
    merged["market_odds_available"] = merged["market_favorite"].fillna("") != ""
    merged["model_market_role"] = np.where(
        ~merged["market_odds_available"],
        "unknown",
        np.where(merged["predicted_winner"] == merged["market_favorite"], "model_favorite", "model_underdog"),
    )
    return merged
