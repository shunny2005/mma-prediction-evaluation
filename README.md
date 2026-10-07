# MMA Prediction: Evaluation Harness and Results

A UFC fight-prediction research project, published as its evaluation harness, data-integrity
tooling, and full out-of-sample results. The predictive model itself is deliberately not in
this repository (see [What is withheld](#what-is-withheld)).

Research only. Nothing here is betting advice, and the results below show the model does
not beat the betting market.

## Headline result

A deployment simulation: train through 2024-12-31, then for each of 68 real UFC events from
2025-01-11 to 2026-08-08, predict every fight, freeze the predictions, and only then reveal
results and update. 835 fights, none seen before being predicted.

| | Result |
| --- | --- |
| Winner accuracy, 5-seed mean | 61.77% (std 0.62pp) |
| Winner accuracy, primary seed | 60.60%, 95% bootstrap CI [57.36%, 63.83%] |
| vs. single-rating Elo baseline (835 fights) | +4.07pp, 95% CI [+0.60, +7.54] |
| vs. sportsbook favorite (603 odds-matched fights) | **-8.62pp**, statistically significant |
| Keeping fighter ratings current vs. a frozen deployment | +4.79pp, 95% CI [+3.30, +6.35] |

The model beat a simple Elo baseline and lost clearly to the market. Both are reported with
their own denominators: odds exist for 603 of the 835 fights, and odds timing (opening vs.
closing) is unknown, so no return-on-investment figure here is a claim of an executable edge.

Full write-up: [`holdout-2025-2026/`](holdout-2025-2026/README.md).

## What is in this repository

| Path | Contents |
| --- | --- |
| `holdout-2025-2026/` | The deployment simulation: methodology, results, model-vs-market comparison, retraining analysis, betting backtest, limitations, every per-fight prediction, and one frozen prediction file per event |
| `audits/ab-symmetry/` | A fighter-order bug (the same matchup gave different probabilities depending on which fighter was listed first) and the evidence that the fix makes `P(A,B) = 1 - P(B,A)` hold exactly |
| `audits/fighter-identity/` | Fighter-name canonicalization: 56 duplicate/fragmented identity groups found and merged with deterministic rules and a reviewed alias table, plus the candidates deliberately not merged |
| `audits/locked-betting-strategy/` | The frozen betting-strategy specification, its audit, and the forward-test plan |
| `src/mma_v4/` | Identity resolution, betting simulation and strategy selection, main-card annotation, shared metrics and bootstrap helpers |
| `scripts/` | Results ingestion and the holdout's baseline, market-comparison, betting, and reporting steps |
| `tests/` | Tests for the code above, plus tests that check the published holdout artifacts for leakage and internal consistency |

## What is withheld

The parts that determine predictive accuracy are kept private:

- the fighter-state builder (how ratings are defined and updated after each fight)
- feature construction and the feature list
- model architecture details, hyperparameters, and training code
- feature matrices, fighter-state snapshots, and trained weights
- per-prediction feature attributions and the ablation studies showing which inputs matter
- the curated fight-statistics dataset

At a high level the private model keeps multi-dimensional Elo-style ratings for each
fighter, updated in strict chronological order, and feeds them to a small neural network
that is order-symmetric by construction, averaged over five seeds and retrained before each
event.

Consequences for this repository:

- The prediction pipeline cannot be re-run from here. Predictions are published as outputs.
- Scripts under `scripts/` are included to show the evaluation logic. Several read private
  inputs (historical odds, the fight table) and will not run without them.
- Model variants are referred to by neutral labels such as `model_v4_active`.
- Some documents mention internal investigations whose reports are not published.

## Running the tests

Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . pytest
pytest -q
```

The holdout tests run against the published artifacts in `holdout-2025-2026/`. They check,
among other things, that no prediction was trained on data from its own or a later event,
that every fight on a card was predicted from the same training cutoff, that the per-event
frozen files still match the consolidated predictions, and that the numbers quoted in the
write-up match the generated metrics file.

## Data sources

Fight results and statistics derive from UFCStats. Historical odds come from public Kaggle
datasets. Provenance and known gaps are documented in
[`holdout-2025-2026/DATA_AUDIT.md`](holdout-2025-2026/DATA_AUDIT.md) and
[`holdout-2025-2026/LIMITATIONS.md`](holdout-2025-2026/LIMITATIONS.md).
