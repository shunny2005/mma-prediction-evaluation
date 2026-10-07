#!/usr/bin/env python3
"""Parts 8, 9, 11, 14: baselines (Elo-only, market favorite, market-implied), the
resume-relevant winner-count comparison, market-disagreement analysis, and the
model+market combination test -- all on the matched fight subset, computed separately
for 2025, 2026, and combined.

Reproduce: PYTHONPATH=src .venv/bin/python scripts/holdout_2025_2026_baselines_market.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from mma_v4.core import expected_calibration_error, merge_local_odds, prediction_metrics
from mma_v4.diagnosis_common import bootstrap_accuracy_ci, paired_bootstrap_diff
from mma_v4.paths import PROJECT_ROOT, V3_ODDS_MATCHED

OUT = PROJECT_ROOT / "holdout-2025-2026"
PRIMARY_SEED = 1701


def implied(o: float) -> float:
    return 100.0 / (o + 100.0) if o > 0 else (-o) / (-o + 100.0)


def load_primary_seed(path: str, seed: int = PRIMARY_SEED) -> pd.DataFrame:
    df = pd.read_csv(OUT / "data" / path, low_memory=False)
    return df[df["seed"] == seed].copy()


def full_metrics(y: np.ndarray, p: np.ndarray, correct: np.ndarray | None = None) -> dict:
    m = prediction_metrics(y, p)
    conf = np.maximum(p, 1 - p)
    corr = correct if correct is not None else ((p >= 0.5).astype(float) == y)
    ece = expected_calibration_error(conf, corr)
    try:
        auc = roc_auc_score(y, p) if len(np.unique(y)) > 1 else float("nan")
    except ValueError:
        auc = float("nan")
    ci = bootstrap_accuracy_ci(y, p)
    return {
        "n": len(y), "correct": int(corr.sum()), "accuracy": m["accuracy"], "log_loss": m["log_loss"],
        "brier_score": m["brier_score"], "ece": ece, "roc_auc": auc,
        "accuracy_ci_low": ci["ci_low_2_5pct"], "accuracy_ci_high": ci["ci_high_97_5pct"],
    }


def main() -> None:
    model = load_primary_seed("event_retrained_all_predictions_multiseed.csv")
    elo = load_primary_seed("elo_only_event_retrained_all_predictions_multiseed.csv")
    model["fight_year"] = pd.to_datetime(model["fight_date"]).dt.year
    elo["fight_year"] = pd.to_datetime(elo["fight_date"]).dt.year

    # ---------------- Merge odds ----------------
    tmp = model.copy()
    merged = merge_local_odds(tmp, V3_ODDS_MATCHED)
    merged["fight_year"] = pd.to_datetime(merged["fight_date"]).dt.year
    market = merged[merged["market_odds_available"] == True].copy()
    market["market_implied_p_a"] = market["fighter_1_odds"].map(implied)
    matched_ids = set(market["fight_id"])
    print(f"Matched odds fights: {len(market)} of {len(model)} total 2025-2026 fights.")

    elo_matched = elo[elo["fight_id"].isin(matched_ids)].merge(market[["fight_id", "fight_year"]], on=["fight_id", "fight_year"], how="inner")
    model_matched = market  # already restricted to matched subset

    # ---------------- Part 8/9/16: headline comparison table ----------------
    rows = []
    for label, yr_filter in [("2025", 2025), ("2026", 2026), ("combined", None)]:
        m_sub = model_matched if yr_filter is None else model_matched[model_matched.fight_year == yr_filter]
        e_sub = elo_matched if yr_filter is None else elo_matched[elo_matched.fight_year == yr_filter]
        model_all_sub = model if yr_filter is None else model[model.fight_year == yr_filter]

        model_metrics_all = full_metrics(model_all_sub["label_a_win"].to_numpy(float), model_all_sub["fighter_a_win_probability"].to_numpy(float))
        elo_all_sub = elo if yr_filter is None else elo[elo.fight_year == yr_filter]
        elo_metrics_all = full_metrics(elo_all_sub["label_a_win"].to_numpy(float), elo_all_sub["fighter_a_win_probability"].to_numpy(float))

        fav_correct = int((m_sub["market_favorite"] == m_sub["actual_winner"]).sum())
        market_m = full_metrics(m_sub["label_a_win"].to_numpy(float), m_sub["market_implied_p_a"].to_numpy(float))
        model_on_matched = full_metrics(m_sub["label_a_win"].to_numpy(float), m_sub["fighter_a_win_probability"].to_numpy(float))
        elo_on_matched = full_metrics(e_sub["label_a_win"].to_numpy(float), e_sub["fighter_a_win_probability"].to_numpy(float))

        rows.append({
            "period": label,
            "fights_predicted_all": len(model_all_sub),
            "model_correct_all": model_metrics_all["correct"], "model_accuracy_all": model_metrics_all["accuracy"],
            "model_log_loss_all": model_metrics_all["log_loss"], "model_brier_all": model_metrics_all["brier_score"],
            "model_accuracy_ci_low": model_metrics_all["accuracy_ci_low"], "model_accuracy_ci_high": model_metrics_all["accuracy_ci_high"],
            "elo_correct_all": elo_metrics_all["correct"], "elo_accuracy_all": elo_metrics_all["accuracy"],
            "elo_log_loss_all": elo_metrics_all["log_loss"],
            "model_minus_elo_correct": model_metrics_all["correct"] - elo_metrics_all["correct"],
            "model_minus_elo_accuracy_pp": (model_metrics_all["accuracy"] - elo_metrics_all["accuracy"]) * 100,
            "matched_market_fights": len(m_sub),
            "model_correct_matched": model_on_matched["correct"], "model_accuracy_matched": model_on_matched["accuracy"],
            "elo_correct_matched": elo_on_matched["correct"], "elo_accuracy_matched": elo_on_matched["accuracy"],
            "market_favorite_correct": fav_correct, "market_favorite_accuracy": fav_correct / len(m_sub) if len(m_sub) else float("nan"),
            "market_implied_accuracy": market_m["accuracy"], "market_implied_log_loss": market_m["log_loss"], "market_implied_brier": market_m["brier_score"],
            "model_minus_market_correct": model_on_matched["correct"] - fav_correct,
            "model_minus_market_accuracy_pp": (model_on_matched["accuracy"] - fav_correct / len(m_sub)) * 100 if len(m_sub) else float("nan"),
        })
        print(f"[{label}] Model: {model_on_matched['correct']}/{len(m_sub)} ({model_on_matched['accuracy']*100:.1f}%)  "
              f"Market favorite: {fav_correct}/{len(m_sub)} ({fav_correct/len(m_sub)*100:.1f}%)  "
              f"Diff: {model_on_matched['correct']-fav_correct:+d} winners ({(model_on_matched['accuracy']-fav_correct/len(m_sub))*100:+.2f}pp)")

    headline = pd.DataFrame(rows)
    headline.to_csv(OUT / "data" / "headline_2025_2026_vs_2025_vs_2026.csv", index=False)

    # ---------------- Paired bootstrap: model vs market favorite (combined matched) ----------------
    y = model_matched["label_a_win"].to_numpy(float)
    p_model = model_matched["fighter_a_win_probability"].to_numpy(float)
    p_market = model_matched["market_implied_p_a"].to_numpy(float)
    paired = {
        "accuracy": paired_bootstrap_diff(y, p_model, p_market, metric="accuracy"),
        "log_loss": paired_bootstrap_diff(y, p_model, p_market, metric="log_loss"),
        "brier_score": paired_bootstrap_diff(y, p_model, p_market, metric="brier_score"),
    }
    with open(OUT / "data" / "model_vs_market_paired_bootstrap.json", "w") as fh:
        json.dump(paired, fh, indent=2)
    print("\nPaired bootstrap model vs market (combined matched):")
    for metric, d in paired.items():
        print(f"  {metric}: diff={d['point_diff_a_minus_b']:+.4f} CI=[{d['ci_low_2_5pct']:+.4f},{d['ci_high_97_5pct']:+.4f}] distinguishable={d['statistically_distinguishable_95pct']}")

    # ---------------- Part 11/14: model vs market disagreement ----------------
    m = model_matched.copy()
    m["predicted_winner_is_a"] = m["fighter_a_win_probability"] >= 0.5
    m["market_favors_a"] = m["market_favorite"] == m["fighter_a_name"]
    m["agrees_with_favorite"] = m["predicted_winner_is_a"] == m["market_favors_a"]
    m["edge"] = (m["fighter_a_win_probability"] - m["market_implied_p_a"]).abs()
    # Predetermined thresholds (matching resume-model-diagnosis's convention; NOT tuned on
    # this 2025-2026 holdout): weak disagreement < 5pp edge, strong >= 5pp edge.
    m["disagreement_bucket"] = np.where(m["agrees_with_favorite"], "agrees_with_favorite", np.where(m["edge"] >= 0.05, "strong_disagreement", "weak_disagreement"))

    def implied_american_from_prob(p: float) -> float:
        return -100 * p / (1 - p) if p >= 0.5 else 100 * (1 - p) / p

    disagreement_rows = []
    for bucket, g in m.groupby("disagreement_bucket"):
        n = len(g)
        correct = int(g["prediction_correct"].sum())
        # fighter_1_odds always corresponds to fighter_a after merge_local_odds' reversed-order
        # fallback (it swaps fighter_1_odds/fighter_2_odds together with the name swap).
        picked_a_mask = g["fighter_a_win_probability"] >= 0.5
        avg_odds = np.where(picked_a_mask, g["fighter_1_odds"], g["fighter_2_odds"]).astype(float).mean()
        # ROI from blindly betting the model's pick at 1 unit flat stake, using that fight's own moneyline for whichever side the model picked.
        stakes, returns = [], []
        for _, r in g.iterrows():
            picked_a = r["fighter_a_win_probability"] >= 0.5
            odds = r["fighter_1_odds"] if picked_a else r["fighter_2_odds"]
            won = (r["actual_winner"] == r["fighter_a_name"]) == picked_a
            profit = (odds / 100.0 if odds > 0 else 100.0 / abs(odds)) if won else -1.0
            stakes.append(1.0)
            returns.append(profit)
        roi = float(np.sum(returns) / np.sum(stakes)) if stakes else float("nan")
        disagreement_rows.append({
            "bucket": bucket, "n": n, "model_correct": correct, "model_accuracy": correct / n if n else float("nan"),
            "mean_edge": float(g["edge"].mean()), "blind_flat_stake_roi": roi, "units_won": float(np.sum(returns)),
        })
    disagreement = pd.DataFrame(disagreement_rows)
    disagreement.to_csv(OUT / "data" / "market_disagreement_analysis.csv", index=False)
    print("\nModel/market disagreement buckets:")
    print(disagreement.to_string(index=False))

    # Strict disagreement (model's predicted winner != market favorite), regardless of edge size.
    strict = m[~m["agrees_with_favorite"]]
    strict_correct = int(strict["prediction_correct"].sum())
    market_correct_when_model_disagrees = int((~strict["prediction_correct"]).sum())  # market favorite wins exactly when model is wrong here, since disagreement means model picked the non-favorite
    print(f"\nWhen model disagreed with market favorite (n={len(strict)}): "
          f"model correct {strict_correct} ({strict_correct/len(strict)*100:.1f}%), "
          f"market favorite correct {market_correct_when_model_disagrees} ({market_correct_when_model_disagrees/len(strict)*100:.1f}%).")

    # ---------------- Part 14: model + market combination, fit on pre-2025 only ----------------
    print("\n=== Model + market combination (combiner trained on pre-2025 data only) ===")
    # Use the existing v4 corrected-model's pre-2025 walk-forward predictions (resume-fixed-a-b)
    # merged with odds as the pre-2025 training set for the combiner, so the combination
    # weights are never fit on 2025-2026 outcomes.
    pre2025 = pd.read_csv(PROJECT_ROOT / "resume-fixed-a-b" / "predictions" / "primary_seed_all_predictions.csv", low_memory=False)
    pre2025 = pre2025[pre2025["seed"] == 1701] if "seed" in pre2025.columns else pre2025
    pre2025_tmp = pre2025.copy()
    pre2025_tmp["predicted_winner"] = pre2025_tmp["fighter_a_name"]
    pre2025_merged = merge_local_odds(pre2025_tmp, V3_ODDS_MATCHED)
    pre2025_market = pre2025_merged[pre2025_merged["market_odds_available"] == True].copy()
    pre2025_market["market_implied_p_a"] = pre2025_market["fighter_1_odds"].map(implied)
    eps = 1e-6

    def to_logit(p):
        pc = np.clip(p, eps, 1 - eps)
        return np.log(pc / (1 - pc))

    x_train = np.column_stack([to_logit(pre2025_market["fighter_a_win_probability"]), to_logit(pre2025_market["market_implied_p_a"])])
    y_train = pre2025_market["label_a_win"].to_numpy(float)
    combiner = LogisticRegression(max_iter=2000).fit(x_train, y_train)
    print(f"Combiner fit on {len(pre2025_market)} pre-2025 odds-matched fights. Weights: model={combiner.coef_[0][0]:.4f}, market={combiner.coef_[0][1]:.4f}")

    x_test = np.column_stack([to_logit(model_matched["fighter_a_win_probability"]), to_logit(model_matched["market_implied_p_a"])])
    p_combo = combiner.predict_proba(x_test)[:, 1]
    combo_m = prediction_metrics(y, p_combo)
    model_m = prediction_metrics(y, p_model)
    market_m2 = prediction_metrics(y, p_market)
    combo_summary = {
        "combiner_model_weight": float(combiner.coef_[0][0]), "combiner_market_weight": float(combiner.coef_[0][1]),
        "combiner_fit_on_n_pre2025_fights": len(pre2025_market),
        "model_only_log_loss": model_m["log_loss"], "market_only_log_loss": market_m2["log_loss"], "combined_log_loss": combo_m["log_loss"],
        "model_only_accuracy": model_m["accuracy"], "market_only_accuracy": market_m2["accuracy"], "combined_accuracy": combo_m["accuracy"],
    }
    with open(OUT / "data" / "model_market_combination_2025_2026.json", "w") as fh:
        json.dump(combo_summary, fh, indent=2)
    print(json.dumps(combo_summary, indent=2))

    # ---------------- Breakdowns: weight class, confidence bucket, history bucket ----------------
    print("\n=== Breakdown by weight class (model, all 2025-2026 fights) ===")
    by_wc = model.groupby("division").apply(lambda g: pd.Series({"n": len(g), "accuracy": g["prediction_correct"].mean()})).reset_index().sort_values("n", ascending=False)
    by_wc.to_csv(OUT / "data" / "breakdown_by_weight_class.csv", index=False)
    print(by_wc.to_string(index=False))

    conf = model["fighter_a_win_probability"].combine(1 - model["fighter_a_win_probability"], max)
    model["confidence_bucket"] = pd.cut(conf, bins=[0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 1.0], include_lowest=True)
    by_conf = model.groupby("confidence_bucket", observed=True).apply(lambda g: pd.Series({"n": len(g), "accuracy": g["prediction_correct"].mean(), "mean_confidence": conf.loc[g.index].mean()})).reset_index()
    by_conf.to_csv(OUT / "data" / "breakdown_by_confidence_bucket.csv", index=False)
    print("\n=== Breakdown by confidence bucket ===")
    print(by_conf.to_string(index=False))

    print("\nWrote all baseline/market/disagreement CSVs and JSONs under holdout-2025-2026/data/")


if __name__ == "__main__":
    main()
