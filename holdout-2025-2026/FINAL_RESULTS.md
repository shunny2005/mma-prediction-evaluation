# Final Results

**Deployment simulation: train through 2024-12-31, then predict-and-freeze every UFC
event from 2025-01-11 through 2026-08-08, one event at a time, retraining after each.**
835 fights, 68 events -- **the latest event with complete, verified box-score data**.
UFC 330 (2026-08-15) was checked and excluded: no box scores for that event exist
anywhere in the repository or the supplied source files, only a pre-fight forecast
(`reports/ufc_330/UFC_330_PREDICTIONS.md`); see `LIMITATIONS.md` for the full check.
Primary result uses the event-retrained variant, 5 predetermined seeds
`[1701..1705]` throughout (including the frozen and state-updated counterfactuals, as
of this cleanup pass -- see `RETRAINING_ANALYSIS.md`).

## Headline table (Part 16)

| Metric | 2025 | 2026 (through Mar 28 for market rows) | Combined |
| --- | ---: | ---: | ---: |
| Fights predicted (full holdout) | 513 | 322 | 835 |
| Model correct (primary seed) | 309 | 197 | 506 |
| Model accuracy (primary seed) | 60.23% | 61.18% | 60.60% |
| Model accuracy (5-seed mean) | -- | -- | **61.77% +/- 0.62pp** |
| Elo-only correct (full holdout, primary seed) | 286 | 186 | 472 |
| Elo-only accuracy | 55.75% | 57.76% | 56.53% |
| Model minus Elo (winners, full holdout) | +23 | +11 | +34 |
| Model minus Elo (pp) | +4.48 | +3.42 | +4.07 |
| **Matched market fights** (subset, not full holdout) | 490 | 113 | **603 of 835 (72.2%)** |
| Model correct (matched subset only) | 292 | 76 | 368 |
| Model accuracy (matched subset only) | 59.59% | 67.26% | 61.03% |
| Market favorite correct (matched subset) | 334 | 86 | 420 |
| Market favorite accuracy (matched subset) | 68.16% | 76.11% | 69.65% |
| Model minus market (winners, matched subset) | **-42** | **-10** | **-52** |
| Model minus market (pp, matched subset) | **-8.57** | **-8.85** | **-8.62** |
| Model log loss (full holdout) | 0.6579 | 0.6491 | 0.6545 |
| Market-implied log loss (matched subset) | 0.5887 | 0.5203 | 0.5759 |

**The "Elo" row uses all 835 fights (Elo is available for every fight). The "matched
market" rows use only the 603 fights with usable historical odds -- these are two
different denominators and are never mixed in the same ratio.** Odds coverage stops
after 2026-03-28, so the "2026" market columns above really mean "Jan 24 - Mar 28 2026
only," not the full 2026 test period. Sources: `data/headline_2025_2026_vs_2025_
vs_2026.csv`, `data/event_retrained_all_predictions_multiseed.csv`.

## Bootstrap confidence interval on accuracy (primary seed, all 835 fights)

95% CI: **[57.36%, 63.83%]** (2,000 resamples). The 5-seed mean of 61.77% and the
primary-seed point estimate of 60.60% both fall comfortably inside this interval.

## Paired comparison vs. market favorite (603-fight matched subset)

| metric | model minus market | 95% CI | statistically distinguishable? |
| --- | ---: | --- | --- |
| accuracy | -9.29pp | [-13.76, -4.98] | **yes** |
| log loss | +0.0748 (worse) | [+0.0475, +0.1030] | **yes** |
| Brier score | +0.0326 (worse) | [+0.0204, +0.0448] | **yes** |

**The model did not beat the sportsbook favorite at predicting winners, on the 603
fights where a comparison is possible.** See `MODEL_VS_MARKET.md` for full detail.

## Paired comparison vs. Elo-only (full 835-fight holdout)

| metric | model minus Elo | 95% CI | statistically distinguishable? |
| --- | ---: | --- | --- |
| accuracy | +4.07pp | [+0.60, +7.54] | **yes** |

**The model did beat a simple overall-Elo-only baseline, on the full holdout.**

## Calibration

Expected calibration error and confidence-bucket breakdown: `data/breakdown_by_
confidence_bucket.csv`. The model is reasonably calibrated in the 50-70% confidence
range but has very few fights in the 70%+ buckets (69 of 835) to say much about
calibration there.

## Retraining (Part 10) -- fair 5-seed comparison, see RETRAINING_ANALYSIS.md

| variant | 5-seed mean accuracy | std |
| --- | ---: | ---: |
| Fully frozen (model + state frozen at 2024-12-31) | 56.10% | 1.68pp |
| State-updated (frozen weights, live state) | 60.89% | 0.78pp |
| Event-retrained (state + weights both update) | 61.77% | 0.62pp |

State updates are what drive the improvement (frozen -> state-updated: +4.79pp,
statistically significant). Retraining model weights on top of already-updated state
adds a small, statistically significant improvement in log loss/Brier score, but the
accuracy improvement specifically is not confidently distinguishable from zero (95% CI
lower bound essentially at zero) -- see `RETRAINING_ANALYSIS.md` for the precise,
metric-by-metric verdict.
