# Retraining Analysis (Part 10)

**Cleanup-pass correction**: the original version of this file compared a 5-seed
event-retrained result against *single-seed* frozen and state-updated results, which is
not a fair comparison. All three deployment variants below now use the identical 5
predetermined seeds `[1701, 1702, 1703, 1704, 1705]` and the identical 835 holdout
fights (verified programmatically -- see `tests/test_v4_2025_2026_holdout_integrity.py`).
Source: `data/retraining_comparison_5seed.json`, `data/fully_frozen_predictions_
multiseed.csv`, `data/state_updated_predictions_multiseed.csv`,
`data/event_retrained_all_predictions_multiseed.csv`.

## Five-seed results, all three variants

| variant | model weights | fighter state | mean accuracy | std | median | min | max | mean log loss | mean Brier |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. Fully frozen | frozen at 2024-12-31 | frozen at 2024-12-31 | 56.10% | 1.68pp | -- | -- | -- | 0.6974 | 0.2516 |
| 2. State-updated | frozen at 2024-12-31 | live, updated after every event | 60.89% | 0.78pp | -- | -- | -- | 0.6557 | 0.2319 |
| 3. Event-retrained (main) | retrained before every event | live, updated after every event | 61.77% | 0.62pp | -- | -- | -- | 0.6519 | 0.2300 |

Per-seed detail (correct/accuracy/log loss/Brier for every one of the 5 seeds,
individually) is in `data/retraining_comparison_5seed.json` under each variant's
`per_seed` list -- not reproduced in full here for length, but every seed's number
contributes to the mean/std above, and no seed was dropped or cherry-picked.

## Paired, seed-matched comparisons (same fights, same seed, 2,000 bootstrap resamples)

| comparison | correct (a vs. b) | accuracy diff | 95% CI | log loss diff | Brier diff | accuracy distinguishable? |
| --- | --- | ---: | --- | ---: | ---: | --- |
| State-updated vs. fully frozen | 2,542 vs. 2,342 (+200) | +4.79pp | [+3.30, +6.35] | -0.0417 | -0.0198 | **yes** |
| Event-retrained vs. state-updated | 2,579 vs. 2,542 (+37) | +0.89pp | [+0.00, +1.77] | -0.0038 | -0.0019 | **no** (CI lower bound is essentially exactly zero) |
| Event-retrained vs. fully frozen | 2,579 vs. 2,342 (+237) | +5.68pp | [+4.10, +7.21] | -0.0455 | -0.0216 | **yes** |

(n=4,175 paired observations per comparison: 835 fights x 5 seeds.)

## Did state updates help versus fully frozen? **YES.**

Keeping fighter rating state current after every event -- without ever touching the
model's weights -- improved accuracy by a statistically significant **+4.79 percentage
points** (95% CI [+3.30pp, +6.35pp], log loss and Brier both significantly better too).
This is the single largest, most confident effect in this analysis.

## Did model-weight retraining help beyond state updates? **NOT CLEARLY -- mixed by metric.**

Event-retrained beats state-updated by +0.89pp on accuracy, but the 95% CI on that
difference is [+0.00pp, +1.77pp] -- the lower bound sits essentially exactly at zero,
so this is **not confidently distinguishable from no effect** on accuracy specifically.
Log loss and Brier score, however, **are** both statistically significantly better for
the retrained variant (smaller CI, entirely below zero on the difference). The honest,
precise statement:

> **Updating fighter state improved performance materially; retraining network weights
> after each event produced a small, statistically significant improvement in
> probability quality (log loss, Brier score) but did not produce a clearly
> distinguishable additional improvement in raw winner accuracy.**

Do not round this up to a clean "retraining helped" or down to "retraining did
nothing" -- both would overstate the precision of what the data actually shows.

## Interpretation

This reinforces, with a fairer comparison than the original draft, the central finding
of an earlier internal model-diagnosis investigation: most of this system's real-world
value comes from disciplined, low-cost state-tracking, not from the neural network's
capacity or from expensive retraining. If a deployed version of this system had to
choose between (a) retraining the full model after every UFC event, or (b) just keeping
fighter ratings current and never touching the model weights again after the initial
2024 training run, this holdout shows (a) buys a small, mostly-probability-quality
improvement over (b) -- real by log loss/Brier, but not confidently more winners
picked correctly.
