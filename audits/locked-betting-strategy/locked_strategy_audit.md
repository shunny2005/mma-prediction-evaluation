# Locked Strategy Audit

- No model retraining occurs in this locked validation workflow.
- The workflow consumes already-created V4 prediction rows with model probabilities.
- Odds are merged only after predictions exist and are used only for evaluation, edge calculation, and payout simulation.
- The locked quarterly selector uses only data strictly before each test quarter for selection.
- Burn-in/default windows are present in the logs but excluded from the headline result.
- Candidate strategy set, thresholds, scoring formula, burn-in rules, minimum bet/window thresholds, sizing rules, favorite/underdog definitions, and edge calculations are frozen.
- Any future tuning should happen only in a separate research branch, not by modifying this locked validation result.