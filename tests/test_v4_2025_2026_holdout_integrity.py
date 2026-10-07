"""Public subset of a private module: shared helpers only. The rest is withheld (see README)."""

from __future__ import annotations
import pandas as pd
import pytest
from mma_v4.core import fighter_id
from mma_v4.paths import PROJECT_ROOT


HOLDOUT_DIR = PROJECT_ROOT / "holdout-2025-2026"


DATA_DIR = HOLDOUT_DIR / "data"


pytestmark = pytest.mark.skipif(not DATA_DIR.exists(), reason="2025-2026 holdout artifacts not generated in this checkout")


@pytest.fixture(scope="module")
def event_retrained_predictions() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "event_retrained_all_predictions_multiseed.csv", low_memory=False)
    df["fight_date"] = pd.to_datetime(df["fight_date"])
    df["latest_training_fight_date"] = pd.to_datetime(df["latest_training_fight_date"])
    return df


@pytest.fixture(scope="module")
def frozen_predictions() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "fully_frozen_predictions.csv", low_memory=False)
    df["fight_date"] = pd.to_datetime(df["fight_date"])
    df["latest_training_fight_date"] = pd.to_datetime(df["latest_training_fight_date"])
    return df


@pytest.fixture(scope="module")
def state_updated_predictions() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "state_updated_predictions.csv", low_memory=False)
    df["fight_date"] = pd.to_datetime(df["fight_date"])
    df["latest_training_fight_date"] = pd.to_datetime(df["latest_training_fight_date"])
    return df


def test_chronology_never_violated_event_retrained(event_retrained_predictions: pd.DataFrame) -> None:
    """max(training_fight_date) < event_date for every single event-retrained prediction."""
    violations = event_retrained_predictions[event_retrained_predictions["latest_training_fight_date"] >= event_retrained_predictions["fight_date"]]
    assert violations.empty, f"{len(violations)} predictions used training data on or after their own event date"


def test_chronology_never_violated_frozen_and_state_updated(frozen_predictions: pd.DataFrame, state_updated_predictions: pd.DataFrame) -> None:
    for df in (frozen_predictions, state_updated_predictions):
        violations = df[df["latest_training_fight_date"] >= df["fight_date"]]
        assert violations.empty


def test_event_atomicity_same_training_state_within_a_card(event_retrained_predictions: pd.DataFrame) -> None:
    """Every fight on the same event, same seed, must have been generated from the exact
    same training cutoff -- no fight on a card can have "seen" another fight's result
    from that same card."""
    for (event_name, fight_date, seed), group in event_retrained_predictions.groupby(["event_name", "fight_date", "seed"]):
        assert group["latest_training_fight_date"].nunique() == 1, (
            f"{event_name} ({fight_date}, seed {seed}) has predictions built from different training cutoffs "
            "within the same event -- mid-card leakage."
        )
        assert (group["latest_training_fight_date"] < group["fight_date"]).all()


def test_retraining_boundary_event_n_only_in_training_for_event_n_plus_1(event_retrained_predictions: pd.DataFrame) -> None:
    """n_train_fights strictly increases from one event to the next by at least the
    number of fights on the prior event (event N's fights enter training for event N+1,
    never for event N itself)."""
    primary = event_retrained_predictions[event_retrained_predictions["seed"] == event_retrained_predictions["seed"].min()]
    per_event = primary.groupby("event_index").agg(n_train_fights=("n_train_fights", "first"), n_fights=("fight_id", "size")).sort_index()
    prior_train = per_event["n_train_fights"].shift(1)
    prior_fights = per_event["n_fights"].shift(1)
    grown = per_event["n_train_fights"] >= (prior_train + prior_fights)
    assert grown.iloc[1:].all(), "Training-set size did not grow by at least the prior event's fight count"


def test_fighter_state_used_for_event_reflects_only_prior_fights(event_retrained_predictions: pd.DataFrame) -> None:
    """The state snapshot date recorded for every prediction (via latest_training_fight_date)
    is strictly before that fight's own event -- i.e. no fighter's rating going into a
    prediction could have been updated by anything on or after that fight's own card."""
    assert (event_retrained_predictions["latest_training_fight_date"] < event_retrained_predictions["fight_date"]).all()


def test_fighter_identity_canonicalization_consistent(event_retrained_predictions: pd.DataFrame) -> None:
    """Every fighter_id in the holdout predictions matches the deterministic canonical
    fighter_id() derived from the corresponding fighter_name -- i.e. every row went
    through the same canonicalization layer as the rest of the pipeline, not a raw,
    unprocessed name."""
    sample = event_retrained_predictions[event_retrained_predictions["seed"] == event_retrained_predictions["seed"].min()]
    mismatches_a = sample[sample["fighter_a_id"] != sample["fighter_a_name"].map(fighter_id)]
    mismatches_b = sample[sample["fighter_b_id"] != sample["fighter_b_name"].map(fighter_id)]
    assert mismatches_a.empty and mismatches_b.empty


def test_no_duplicate_fight_keys_in_holdout_predictions(event_retrained_predictions: pd.DataFrame) -> None:
    per_seed = event_retrained_predictions.groupby("seed")
    for seed, group in per_seed:
        assert not group["fight_id"].duplicated().any(), f"Duplicate fight_id within seed {seed}'s predictions"


def test_dataset_completeness_no_holdout_event_missing_results() -> None:
    ledger = pd.read_csv(DATA_DIR / "fight_ledger_2025_2026.csv", low_memory=False)
    missing_winner = ledger[ledger["actual_winner"].isna() & ledger["label_a_win"].notna()]
    assert missing_winner.empty, "A completed holdout fight is missing its actual winner"
    missing_label = ledger[ledger["label_a_win"].isna()]
    assert missing_label.empty, (
        f"{len(missing_label)} holdout fights have no label_a_win -- either an undocumented "
        "draw/no-contest slipped through, or a result is genuinely missing"
    )


def test_prediction_files_immutable_and_match_consolidated_file() -> None:
    """Every per-event frozen prediction file's rows exist, unchanged, in the
    consolidated all_predictions.csv -- i.e. the per-event snapshot and the combined
    file were never allowed to diverge after the fact."""
    all_preds = pd.read_csv(DATA_DIR / "all_predictions.csv", low_memory=False).set_index("fight_id")
    event_files = list((HOLDOUT_DIR / "event_predictions").glob("*.csv"))
    assert len(event_files) == 68, f"Expected 68 per-event prediction files, found {len(event_files)}"
    for path in event_files:
        event_df = pd.read_csv(path, low_memory=False)
        for _, row in event_df.iterrows():
            assert row["fight_id"] in all_preds.index, f"{row['fight_id']} from {path.name} missing in all_predictions.csv"
            consolidated_prob = all_preds.loc[row["fight_id"], "fighter_a_win_probability"]
            assert abs(float(consolidated_prob) - float(row["fighter_a_win_probability"])) < 1e-9, (
                f"Prediction for {row['fight_id']} in {path.name} does not match all_predictions.csv -- "
                "possible post-hoc regeneration/divergence."
            )


def test_no_2025_2026_fight_used_in_frozen_december_2024_training() -> None:
    """The frozen-checkpoint training cutoff (recorded in every prediction row) never
    reaches into 2025 -- confirms the Part 1 requirement that the initial model knows
    nothing after 2024-12-31."""
    frozen = pd.read_csv(DATA_DIR / "fully_frozen_predictions.csv", low_memory=False)
    assert (pd.to_datetime(frozen["latest_training_fight_date"]) <= pd.Timestamp("2024-12-31")).all()
    state_updated = pd.read_csv(DATA_DIR / "state_updated_predictions.csv", low_memory=False)
    assert (pd.to_datetime(state_updated["latest_training_fight_date"]) <= pd.Timestamp("2024-12-31")).all()
