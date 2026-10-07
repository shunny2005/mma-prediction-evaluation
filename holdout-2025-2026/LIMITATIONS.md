# Limitations

## Evaluation cutoff: UFC 330 (2026-08-15) checked and excluded

The snapshot date of this write-up is 2026-08-18, but the evaluation itself runs only
through **2026-08-08**, the latest UFC event with complete, verified box-score data.
UFC 330: Makhachev vs. Machado Garry (2026-08-15) was searched for across the fight
table, the update patches, and the supplied source files before finalizing this cutoff.
Only a pre-fight forecast existed for it, not results or box scores.

No complete box scores (strikes, takedowns, control time -- needed for rating updates,
not just a winner) for UFC 330 were found anywhere. Results-only data was not used to
reconstruct missing stats, and the cutoff was kept at 2026-08-08 rather than inventing
partial coverage.

## Odds timing: still UNKNOWN

Source files, scripts, and documentation were checked for an explicit
opening/closing/snapshot/consensus timestamp declaration. The odds actually used
(`mdabbert/ultimate-ufc-dataset`, a public Kaggle dataset) are documented only as
"American moneyline" -- no timing convention is stated in the dataset's own columns or
documentation. Two alternative sources considered and rejected
(`mdabbert/ufc-fights-2010-2020-with-betting-odds`, `jerzyszocik/ufc-betting-odds-
daily-dataset`) also lack an explicit timing declaration, though the `jerzyszocik`
source carries an `adding_date` column that was never cross-referenced against
`event_date` (a possible future avenue, not pursued here to avoid making an unverified
claim from an unused source).

**Classification: UNKNOWN.**

> Historical odds backtest only. Real-time executable ROI is not established because
> the odds timestamp is unknown.

This qualification applies to every ROI, edge, and market-comparison number in this
write-up (`FINAL_RESULTS.md`, `MODEL_VS_MARKET.md`, `BETTING_RESULTS.md`) and must be
carried forward into any external use of these numbers.

## Odds/market coverage gap after March 2026

Matched-odds fights in this holdout stop appearing after 2026-03-28, even though the
raw odds source's overall date range nominally extends to 2026-06-30. Every event from
2026-04-04 onward (15 events, 151 fights) has **zero** matched-odds fights -- not
partial coverage, none at all. This means every market-comparison, disagreement, and
betting number that involves 2026 is effectively built from **only the first ~2.5
months of 2026** (Jan 24 - Mar 28), not the full 2026 test period through August. The
"2026" column throughout the market/betting tables should be read with that caveat: it
is representative of early 2026 only. Model-only and Elo-only accuracy figures (which
don't need odds) are unaffected and do cover the full period through 2026-08-08.

## Box-score data provenance

Fights from 2025-01-11 through 2026-03-28 come from a CSV reconstructed from the public
`Greco1899/scrape_ufc_stats` UFCStats mirror rather than downloaded directly from
ufcstats.com. That mirror's fidelity to ufcstats.com was not independently verified
beyond the checks already performed (all 636 fights have complete box scores, no nulls
in any core stat field, event/date structure matches a Wikipedia cross-check for
spot-checked events, card sizes are uniformly plausible). It is treated as
UFCStats-derived historical data with that documented provenance. Fights from
2026-04-04 onward were verified via a direct ufcstats.com scrape.

## Repeated historical model development on overlapping data

This holdout followed three earlier audit rounds on the same codebase (a fighter-order
symmetry fix; fighter-identity and rating fixes; a feature/architecture diagnosis). The
architecture, hyperparameters, and the specific 122-feature set locked for this
experiment were selected using nested validation and diagnostic evidence gathered
entirely on pre-2025 data -- not tuned on this 2025-2026 holdout. However, the codebase
had been extensively analyzed before this holdout was run, so while the holdout was
never peeked at for architecture decisions, it is not being evaluated with zero prior
exposure to this dataset's general behavior. This is disclosed as an epistemic caveat,
not a specific bug.

## Remaining data-integrity notes

- Two data corruption issues were found and fixed during this experiment's setup, both
  documented in `DATA_AUDIT.md`: the originally-reported Jan-2025-to-Mar-2026 gap, and
  a previously-undetected secondary corruption inside the "already verified"
  April-August 2026 window (leftover unmatched placeholder duplicates). Both were fixed
  via an unconditional supersession rule (verified ufcstats-sourced data always wins
  its full covered date range) before any prediction was generated.
- One feature family cannot be exactly reconstructed for the "fully frozen" and
  "state-updated" counterfactual arms because the raw win-history list isn't stored in
  the snapshot format used for state reconstruction; those two arms fall back to the
  "no history" default for that family. This does not affect the primary
  event-retrained result, which uses live, fully-populated state throughout.
- `is_main_card` was not reconstructed for the betting evaluation in this holdout (set
  to `False` for all fights), so there is no main-card-specific ROI breakdown here.
- The locked quarterly betting selector is a freshly-bootstrapped reproduction within
  this holdout window, not a literal continuation of the original selector's internal
  state (see `METHODOLOGY.md` and `BETTING_RESULTS.md`).
