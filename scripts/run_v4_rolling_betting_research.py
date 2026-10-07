#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mma_v4.paths import MATCHUP_FEATURES, REPORTS_DIR
from mma_v4.rolling_betting import run_rolling_walk_forward


def main() -> None:
    predictions_path = REPORTS_DIR / "v4_predictions" / "ablations" / "model_v4_prior" / "all_predictions.csv"
    output_dir = REPORTS_DIR / "betting_optimization" / "rolling_walk_forward"
    outputs = run_rolling_walk_forward(predictions_path, MATCHUP_FEATURES, output_dir)
    print(
        "Wrote rolling walk-forward betting research: "
        f"{len(outputs['comparison'])} comparison rows, "
        f"{len(outputs['selection_log'])} selection windows, "
        f"{len(outputs['selected_bet_log'])} selected bets."
    )


if __name__ == "__main__":
    main()
