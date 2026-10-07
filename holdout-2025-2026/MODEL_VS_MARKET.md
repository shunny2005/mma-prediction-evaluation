# Model vs. Market

## Market coverage (read this before any number below)

The full holdout is **835 fights**. Historical moneyline odds could only be matched for
**603 of those 835 fights (72.2%)**. Odds matching stops after **2026-03-28** -- no
fight from 2026-04-04 onward (15 events, 151 fights) has a usable odds record. Every
number in this file uses the 603-fight matched subset, **never** the full 835.

| | count |
| --- | ---: |
| Total holdout fights | 835 |
| Fights with usable odds | 603 |
| Coverage | 72.2% |
| 2025 matched fights | 490 |
| 2026 matched fights | 113 |
| Last usable odds date | 2026-03-28 |

**On the 603 holdout fights with usable historical odds, the model predicted 368
winners correctly versus 420 for the sportsbook favorite.** This comparison does not,
and cannot, cover all 835 holdout fights -- do not describe it that way anywhere.

## Part 9: the winner comparison (matched subset only)

| | 2025 (n=490) | 2026 (n=113) | Combined (n=603) |
| --- | ---: | ---: | ---: |
| Model correct | 292 | 76 | **368** |
| Market favorite correct | 334 | 86 | **420** |
| Difference in winners | -42 | -10 | **-52** |
| Difference in accuracy | -8.57pp | -8.85pp | **-8.62pp** |

Note the 2026 row above is really "early 2026 only" (Jan 24 - Mar 28), not the full
2026 test period through August -- see the coverage table above.

## Did the model beat the market favorite: **NO.**

Paired bootstrap (603 matched fights, 2,000 resamples, same fights both sides):
accuracy difference -9.29pp, 95% CI [-13.76pp, -4.98pp] -- entirely below zero, i.e.
statistically distinguishable from "no difference." Log loss and Brier score are both
significantly worse for the model than for the raw market-implied probability
(`data/model_vs_market_paired_bootstrap.json`).

## Full-holdout model accuracy (a different denominator -- do not mix with the above)

Model accuracy across the entire 835-fight holdout (5-seed mean): **61.77% +/-
0.62pp**. This number uses all 835 fights and is not comparable, row for row, to the
603-fight matched-market numbers above; they answer different questions (raw model
skill vs. model-vs-market on the fights where both exist).

## Part 11/14: disagreement analysis (matched subset, n=603)

Predetermined thresholds (not tuned on this holdout): "agrees" = model's pick matches
the market favorite; "weak disagreement" = model picks the other side with <5pp of
edge; "strong disagreement" = model picks the other side with >=5pp of edge.

| bucket | n | model correct | model accuracy | blind flat-stake ROI |
| --- | ---: | ---: | ---: | ---: |
| Agrees with favorite | 415 | 300 | 72.3% | -0.44% |
| Weak disagreement | 8 | 5 | 62.5% | +27.75% (n=8, not meaningful) |
| Strong disagreement | 180 | 63 | 35.0% | -4.50% |

**When the model disagrees with the market favorite at all (n=188, weak+strong
combined, all within the 603-fight matched subset): model correct 68 times (36.2%),
market favorite correct 120 times (63.8%).** The market was right roughly 1.8x as
often as the model on exactly the fights where they disagreed.

## Model + market combination (Part 14)

Combiner (2-feature logistic regression on [model logit, market logit]) was fit
**exclusively on 3,200 pre-2025 odds-matched fights** from the existing corrected
model's walk-forward predictions -- never on any 2025-2026 outcome -- then applied
unchanged to the 603-fight 2025-2026 matched subset.

| | model only | market only | combined |
| --- | ---: | ---: | ---: |
| Log loss | 0.6507 | 0.5759 | 0.5745 |
| Accuracy | 61.03% | 70.32% | 69.82% |

Combining gives a marginal log-loss improvement over market-alone (0.5759 -> 0.5745)
but a slightly *worse* accuracy (70.3% -> 69.8%) -- a mixed, small, not clearly
meaningful effect either way. **The model does not add a clear, reliable improvement
over the market alone on this holdout.**
