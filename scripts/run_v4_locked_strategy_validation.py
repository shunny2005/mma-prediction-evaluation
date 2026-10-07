#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mma_v4.locked_strategy_validation import run_locked_strategy_validation
from mma_v4.paths import MATCHUP_FEATURES, REPORTS_DIR


def main() -> None:
    predictions_path = REPORTS_DIR / "v4_predictions" / "ablations" / "model_v4_prior" / "all_predictions.csv"
    rolling_report_dir = REPORTS_DIR / "betting_optimization" / "rolling_walk_forward"
    output_dir = REPORTS_DIR / "betting_optimization" / "locked_strategy_validation"
    outputs = run_locked_strategy_validation(predictions_path, MATCHUP_FEATURES, rolling_report_dir, output_dir)
    print(
        "Wrote locked strategy validation: "
        f"{len(outputs['results'])} result rows, "
        f"{len(outputs['bet_log'])} bet-log rows."
    )


if __name__ == "__main__":
    main()
