# Methodology

Model internals (rating definitions, feature list, architecture details, and
hyperparameters) are withheld from this repository; see the top-level README. This
document covers the experimental design, which is what the results depend on for their
validity.

## Deployment simulation design

Treat 2025-01-01 as deployment day. Train once on everything known through
2024-12-31. Then, for every UFC event in chronological order:

1. Build fighter state and generate features using only fights strictly before that
   event's date.
2. (Event-retrained variant only) retrain the model from scratch on every fight
   strictly before that event's date.
3. Generate predictions for every fight on the event.
4. **Freeze those predictions** -- written to `event_predictions/` before any result
   from that event is used anywhere.
5. Only then reveal the event's results, update fighter ratings/state, and add the
   event's fights to the training set for the next event.

No fight ever updates state or retrains the model until every fight on its own card has
already been predicted and frozen. No later event's result can influence an earlier
event's prediction.

## Frozen January-1-2025 checkpoint

- Trained on 8,104 fights with `fight_date <= 2024-12-31`.
- Feature set: 122 features, locked before the holdout was run (see below).
- Architecture: an order-symmetric neural network, identical to the one already locked
  in earlier audit rounds. Not re-tuned for this experiment.
- Seeds: 5 predetermined seeds `[1701, 1702, 1703, 1704, 1705]`, used for all three
  deployment variants.
- Calibration: per-model temperature scaling fit on a chronological 20% validation
  slice of that model's own training data -- unchanged for this experiment.

## Locked feature set

Before touching any 2025-2026 data, two rating dimensions that had failed a
construct-validity check were reviewed using only pre-2025 evidence:

- **One was excluded.** Its update formula computed the identical value for both
  fighters in a fight, so it could not carry fighter-specific information by
  construction -- a code-level defect confirmed by inspection, not by looking at any
  2025-2026 result.
- **One was retained.** It failed a similar check for a harder, non-code reason (the
  underlying signal is rare and near-binary), so removing it was not as clearly
  justified. It was kept, with the weakness documented rather than acted on.

This decision was made and the code changed before the event replay was ever run. It
was not revisited after seeing any 2025-2026 result.

## Deployment variants

Three variants, evaluated on the exact same 835 holdout fights:

1. **Fully frozen** -- model trained once on data through 2024-12-31, scored against
   each fighter's state exactly as it was on 2024-12-31 (ignoring every 2025-2026
   result, even for an August 2026 fight). Reconstructed from stored state snapshots,
   with one disclosed approximation: one feature family needs each fighter's raw
   recent-win history, which is not stored in the snapshot format, so frozen fighters
   fall back to the "no qualifying history" default for that family only. This affects
   only the frozen/state-updated counterfactual arms, never the primary result.
2. **State-updated** -- the identical frozen model weights from #1, but scored against
   each fighter's true, chronologically-correct pre-fight state.
3. **Event-retrained (the main experiment)** -- state updates plus a full model
   retrain before every event, as described above.

## Locked betting strategies

The same rule/sizing configs published in `audits/locked-betting-strategy/` --
`confidence_ge_0.6__shrunk_kelly_s0.5_k0.25_cap_0.5pct`,
`underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct`,
`favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct`, `edge_ge_0.05__flat_1u` --
rerun via the project's own mechanical bet-simulation functions (`bets_for_rule`,
`simulate_bets` in `src/mma_v4/betting.py`), which have no year dependency. The
higher-level research wrappers were not reused because they hardcode a 2021-2025 test
range, which would silently drop every 2026 fight; see
`scripts/holdout_2025_2026_betting.py`'s module docstring. The locked quarterly
selector is reproduced in spirit (re-score candidates from strictly-prior data each
quarter, require a minimum evidence bar) but freshly bootstrapped within the 2025-2026
window rather than carrying forward the internal state of the original selector -- a
disclosed simplification, not presented as identical to the original mechanism.

## What was NOT changed after seeing 2025-2026 results

Architecture, feature definitions (beyond the pre-registered exclusion above),
hyperparameters, seeds, calibration method, and betting thresholds were all locked
before the event replay was run and were not modified afterward. Two implementation
bugs were found and fixed during development of the replay engine itself, before any
result was inspected: a leftover-placeholder-duplicate bug in the April-August 2026
import window, and a fight-metadata-clobbering bug in the frozen-state reconstruction.
Both are data-pipeline fixes made before any holdout number was computed.
