#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mma_v4.betting import run_betting_research
from mma_v4.paths import MATCHUP_FEATURES, REPORTS_DIR


def main() -> None:
    predictions_path = REPORTS_DIR / "v4_predictions" / "ablations" / "model_v4_prior" / "all_predictions.csv"
    output_dir = REPORTS_DIR / "v4_betting"
    outputs = run_betting_research(predictions_path, MATCHUP_FEATURES, output_dir)
    print(
        "Wrote betting research reports: "
        f"{len(outputs['betting_predictions'])} prediction rows with odds, "
        f"{len(outputs['strategy_grid'])} strategy summaries."
    )


if __name__ == "__main__":
    main()
