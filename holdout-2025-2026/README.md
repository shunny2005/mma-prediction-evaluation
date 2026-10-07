# 2025-2026 Event-Holdout Deployment Simulation

> **How would this MMA model actually have performed if it had been deployed at the
> start of 2025, given real UFCStats box scores after every event, and retrained before
> each next event?**

Train through 2024-12-31. Then, for every one of 68 real UFC events from 2025-01-11
through **2026-08-08 -- the latest event with complete, verified box-score data**, in
chronological order: build state from strictly-prior fights, retrain, predict every
fight on that event, **freeze the predictions**, only then reveal results, update
fighter state, and move to the next event. 835 fights, never a later result touching an
earlier prediction (enforced by automated tests, see
`tests/test_v4_2025_2026_holdout_integrity.py`). UFC 330 (2026-08-15) was checked and
excluded for lack of box-score data -- see `LIMITATIONS.md`.

## Headline result

**60.60% winner accuracy (5-seed mean: 61.77% +/- 0.62pp) across 835 genuinely
out-of-sample fights.** Beat a simple overall-Elo baseline (full 835-fight holdout) by
a statistically significant +4.07 percentage points. **On the 603 of 835 holdout fights
(72.2%) with usable historical odds**, lost to the sportsbook favorite by a
statistically significant -8.62 percentage points (368/603 vs. 420/603 correct).
Retraining after every event helps -- a fair, same-5-seeds comparison shows keeping
fighter state current (state-updated vs. fully-frozen: +4.79pp, significant) drives
almost all of the gain; retraining the model's weights on top of that adds a small,
significant improvement in log loss/Brier score but not a clearly distinguishable
further gain in raw accuracy. Full detail in `FINAL_RESULTS.md`.

## Read in this order

1. **`FINAL_RESULTS.md`** -- the headline numbers, 2025 vs. 2026 vs. combined, with
   explicit denominators for every comparison (full 835-fight holdout vs. the
   603-fight market-matched subset -- never mixed).
2. **`DATA_AUDIT.md`** -- how the 2025-2026 box-score dataset was integrated,
   reconciled, and used to fix two rounds of data corruption.
3. **`METHODOLOGY.md`** -- the experimental design.
4. **`FIGHT_LEDGER.md`** / `data/fight_ledger_2025_2026.csv` -- every fight used.
5. **`EVENT_BY_EVENT.md`** -- all 68 events, no cherry-picking.
6. **`MODEL_VS_MARKET.md`** -- the matched-subset winner comparison (leads with the
   coverage numbers: 603 of 835 fights, 72.2%, coverage stops after 2026-03-28), paired
   significance tests, and disagreement analysis.
7. **`RETRAINING_ANALYSIS.md`** -- the frozen/state-updated/event-retrained three-way
   comparison, run across the identical 5 seeds for all three variants.
8. **`BETTING_RESULTS.md`** -- all 5 locked strategies. **3 of 5 were profitable** on
   this window; read the caveats there before drawing any conclusion from that.
9. **`LIMITATIONS.md`** -- the UFC 330 inclusion check, odds timing (still
   unresolved), the real odds-coverage gap after March 2026, and other caveats.

## Data folders

- `data/` -- every machine-readable CSV/JSON referenced above.
- `event_predictions/` -- one frozen, immutable prediction file per UFC event (68
  files), each written before that event's results were used anywhere downstream.
- `resume_metrics_2026-08-18.json` -- the generated metrics snapshot every headline
  number is checked against.

## What was NOT done

Architecture, feature definitions, hyperparameters, seeds, calibration, and betting
thresholds were locked before this holdout was evaluated and were not changed
afterward. A later cleanup pass fixed reporting/evaluation consistency only (fair
same-seed retraining comparison, correct betting count, explicit market-subset
wording, and the Aug-15 cutoff check) -- it did not touch the model, features, or
thresholds.

## Reproduction

The prediction step depends on the private model and cannot be re-run from this
repository (see the top-level README). The published artifacts can be checked with:

```bash
pytest -q
```

Fixed seeds throughout (`[1701..1705]`, used for all three deployment variants).
