from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

V3_ROOT = PROJECT_ROOT.parent / "v3"
V3_CANONICAL_FIGHTS = V3_ROOT / "data" / "processed" / "canonical_fights.csv"
V3_CHRONOLOGICAL_FIGHTS = V3_ROOT / "data" / "processed" / "fights_chronological.csv"
V3_ODDS_MATCHED = V3_ROOT / "reports" / "market_edge" / "predictions_with_market_odds.csv"

CANONICAL_FIGHTS = DATA_DIR / "processed" / "canonical_fights.csv"
CHRONOLOGICAL_FIGHTS = DATA_DIR / "processed" / "fights_chronological.csv"
FIGHTER_STATE = DATA_DIR / "v4_fighter_latest_state.csv"
STATE_SNAPSHOTS = DATA_DIR / "v4_fighter_state_snapshots.csv"
MATCHUP_FEATURES = DATA_DIR / "v4_matchup_features.csv"
CLUSTER_DB = DATA_DIR / "v4_fighter_clusters.sqlite"
IDENTITY_ALIASES = DATA_DIR / "identity_aliases.csv"

