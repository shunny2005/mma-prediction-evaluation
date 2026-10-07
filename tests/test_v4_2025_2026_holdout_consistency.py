"""Regression tests for the 2025-2026 event-holdout cleanup pass (Part 11).

These guard specifically against the class of bugs found in that pass: prose that
disagrees with the underlying computed data, an unfair (mismatched-seed) retraining
comparison, a market-comparison denominator that silently exceeds the odds-matched
fight count, and a reported cutoff that doesn't match what's actually in the dataset.
"""
from __future__ import annotations

import json
import re

import pandas as pd
import pytest

from mma_v4.paths import PROJECT_ROOT

HOLDOUT_DIR = PROJECT_ROOT / "holdout-2025-2026"
DATA_DIR = HOLDOUT_DIR / "data"

pytestmark = pytest.mark.skipif(not DATA_DIR.exists(), reason="2025-2026 holdout artifacts not generated in this checkout")


@pytest.fixture(scope="module")
def resume_metrics() -> dict:
    return json.loads((HOLDOUT_DIR / "resume_metrics_2026-08-18.json").read_text())


def test_betting_profitable_count_matches_computed_value(resume_metrics: dict) -> None:
    betting = pd.read_csv(DATA_DIR / "betting_results.csv")
    fresh_profitable = int((betting["roi"] > 0).sum())
    fresh_total = len(betting)
    assert resume_metrics["betting_profitable_strategies"] == fresh_profitable
    assert resume_metrics["betting_total_strategies"] == fresh_total


def test_betting_prose_matches_computed_profitable_count(resume_metrics: dict) -> None:
    """Guards against exactly the bug this cleanup pass fixed: prose stating a
    different profitable-strategy count than the underlying data."""
    expected = f"{resume_metrics['betting_profitable_strategies']} of {resume_metrics['betting_total_strategies']}"
    wrong_count = resume_metrics["betting_total_strategies"] - resume_metrics["betting_profitable_strategies"]
    wrong_phrase_variants = [f"{n} of {resume_metrics['betting_total_strategies']} profitable" for n in range(resume_metrics["betting_total_strategies"] + 1) if n != resume_metrics["betting_profitable_strategies"]]
    for doc_name in ["BETTING_RESULTS.md", "README.md"]:
        text = (HOLDOUT_DIR / doc_name).read_text()
        for wrong in wrong_phrase_variants:
            assert wrong not in text, f"{doc_name} contains stale/incorrect count phrase '{wrong}'"


def test_retraining_comparison_uses_identical_seeds_and_fights() -> None:
    frozen = pd.read_csv(DATA_DIR / "fully_frozen_predictions_multiseed.csv", low_memory=False)
    state_updated = pd.read_csv(DATA_DIR / "state_updated_predictions_multiseed.csv", low_memory=False)
    event_retrained = pd.read_csv(DATA_DIR / "event_retrained_all_predictions_multiseed.csv", low_memory=False)

    seeds_frozen = set(frozen["seed"].unique())
    seeds_state = set(state_updated["seed"].unique())
    seeds_retrained = set(event_retrained["seed"].unique())
    assert seeds_frozen == seeds_state == seeds_retrained, (
        f"Seed sets differ across deployment variants: frozen={seeds_frozen}, "
        f"state_updated={seeds_state}, event_retrained={seeds_retrained}"
    )
    assert seeds_frozen == {1701, 1702, 1703, 1704, 1705}

    fights_frozen = set(frozen["fight_id"].unique())
    fights_state = set(state_updated["fight_id"].unique())
    fights_retrained = set(event_retrained["fight_id"].unique())
    assert fights_frozen == fights_state == fights_retrained, "Fight sets differ across deployment variants"

    # Every seed must have predicted every fight in every variant (no partial coverage).
    for df, name in [(frozen, "frozen"), (state_updated, "state_updated"), (event_retrained, "event_retrained")]:
        counts = df.groupby("seed").size()
        assert counts.nunique() == 1, f"{name} has uneven fight counts per seed: {counts.to_dict()}"


def test_resume_metrics_json_matches_retraining_comparison_file() -> None:
    retraining = json.loads((DATA_DIR / "retraining_comparison_5seed.json").read_text())
    resume_metrics = json.loads((HOLDOUT_DIR / "resume_metrics_2026-08-18.json").read_text())
    assert abs(resume_metrics["frozen_5seed_mean_accuracy"] - retraining["fully_frozen"]["mean_accuracy"]) < 1e-9
    assert abs(resume_metrics["state_updated_5seed_mean_accuracy"] - retraining["state_updated"]["mean_accuracy"]) < 1e-9
    assert abs(resume_metrics["event_retrained_5seed_mean_accuracy"] - retraining["event_retrained"]["mean_accuracy"]) < 1e-9


def test_markdown_headline_numbers_present_in_resume_metrics_json(resume_metrics: dict) -> None:
    """Every headline number quoted in FINAL_RESULTS.md must be traceable to (present
    somewhere in) the authoritative JSON snapshot -- a lightweight cross-check that the
    markdown wasn't hand-edited to drift from the generated numbers."""
    final_results_text = (HOLDOUT_DIR / "FINAL_RESULTS.md").read_text()

    def fmt_pct(value: float, decimals: int = 2) -> str:
        return f"{value * 100:.{decimals}f}"

    key_numbers = [
        fmt_pct(resume_metrics["model_5seed_mean_accuracy"]),
        fmt_pct(resume_metrics["event_retrained_5seed_mean_accuracy"]),
        str(resume_metrics["fights_tested"]),
        str(resume_metrics["events_tested"]),
        str(resume_metrics["market_matched_fights"]),
    ]
    for number in key_numbers:
        assert number in final_results_text, f"'{number}' from resume_metrics JSON not found in FINAL_RESULTS.md"


def test_market_comparison_denominator_never_exceeds_matched_fights(resume_metrics: dict) -> None:
    model_vs_market = pd.read_csv(DATA_DIR / "model_vs_market.csv", low_memory=False)
    assert len(model_vs_market) == resume_metrics["market_matched_fights"]
    assert resume_metrics["market_matched_fights"] <= resume_metrics["fights_tested"]
    assert resume_metrics["market_correct"] <= resume_metrics["market_matched_fights"]
    assert resume_metrics["model_correct_on_market_subset"] <= resume_metrics["market_matched_fights"]


def test_market_wording_never_implies_full_holdout_denominator() -> None:
    """Guards against sentences like "the model was compared against the sportsbook
    across all 835 fights" -- the market comparison must always name the matched
    subset explicitly."""
    for doc_name in ["MODEL_VS_MARKET.md", "FINAL_RESULTS.md", "README.md"]:
        text = (HOLDOUT_DIR / doc_name).read_text()
        assert "across all 835" not in text.lower().replace("_", " ")
        assert "compared against the sportsbook across all" not in text.lower()


def test_no_completed_fight_after_reported_cutoff(resume_metrics: dict) -> None:
    """Guards the FROZEN holdout-2025-2026 deliverable, not live data: every
    other test in this module reads `DATA_DIR` (this deliverable's own saved
    `holdout-2025-2026/data/` snapshot), not the live `CANONICAL_FIGHTS` table
    which is expected to keep advancing as new events are ingested for later work
    (e.g. UFC 330 was deliberately backfilled after this deliverable's 2026-08-18
    snapshot date, for an unrelated later prediction task). This test previously read
    live `CANONICAL_FIGHTS`, which made it fail the moment the repo's data legitimately
    moved past this deliverable's cutoff -- switched to the deliverable's own frozen
    `event_results.csv` to match every sibling test in this file."""
    events = pd.read_csv(DATA_DIR / "event_results.csv")
    events["fight_date"] = pd.to_datetime(events["fight_date"], errors="coerce")
    cutoff = pd.Timestamp(resume_metrics["cutoff_date"])
    after_cutoff = events[events["fight_date"] > cutoff]
    # The specific check that matters is that the event named in the task as excluded
    # (UFC 330, 2026-08-15) is not present with box scores in this deliverable's own
    # frozen event list.
    ufc_330 = after_cutoff[after_cutoff["event_name"].astype(str).str.contains("330", na=False)]
    assert ufc_330.empty, "UFC 330 (or another event containing '330') found in the frozen holdout deliverable's event list after the reported cutoff"


def test_cutoff_date_matches_latest_event_in_event_results() -> None:
    events = pd.read_csv(DATA_DIR / "event_results.csv")
    resume_metrics = json.loads((HOLDOUT_DIR / "resume_metrics_2026-08-18.json").read_text())
    assert events["fight_date"].max() == resume_metrics["cutoff_date"]


def test_retraining_verdict_wording_is_precise(resume_metrics: dict) -> None:
    """The retraining verdict must not claim a plain "retraining helped" if the
    accuracy gain from weight retraining specifically was not distinguishable from
    zero -- checked programmatically against the underlying CI, not just read by eye."""
    ci_low, ci_high = resume_metrics["retraining_beyond_state_ci"]
    accuracy_distinguishable = resume_metrics["retraining_beyond_state_accuracy_distinguishable"]
    assert accuracy_distinguishable == (ci_low > 0 or ci_high < 0)
    verdict = resume_metrics["retraining_verdict"]
    if not accuracy_distinguishable:
        assert "not" in verdict.lower() and ("distinguishable" in verdict.lower() or "accuracy" in verdict.lower()), (
            "Retraining verdict text does not qualify the accuracy claim despite an inconclusive accuracy CI"
        )
