# Betting Results (Part 12)

Every locked strategy rerun on strictly pre-event predictions (event-retrained,
primary seed 1701) with historical odds, no threshold tuned on this holdout. 603
eligible (odds-matched) fights out of 835 total holdout fights (72.2% coverage; odds
matching stops after 2026-03-28 -- see `MODEL_VS_MARKET.md`). Source:
`data/betting_results.csv`, `data/betting_bet_log_fixed_strategies.csv`,
`data/locked_quarterly_selector_bet_log.csv`.

**All five strategies are shown, not only the profitable ones.**

| strategy | bets | wins | losses | win rate | units wagered | units won/lost | ROI | max drawdown | avg odds | 2025 bets / ROI | 2026 bets / ROI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Confidence >=0.6, shrunk Kelly | 71 | 31 | 40 | 43.7% | 35.84 | +3.32 | **+9.25%** | -3.74% | +83 | 61 / +10.86% | 10 / -0.97% |
| Underdog edge >=0.03 | 38 | 18 | 20 | 47.4% | 9.53 | +0.55 | **+5.74%** | -1.49% | +123 | 34 / -0.22% | 4 / +56.52% (n=4) |
| Favorite edge >=0.075 | 12 | 7 | 5 | 58.3% | 2.99 | -0.15 | **-5.17%** | -0.84% | -154 | 9 / -9.79% | 3 / +8.67% (n=3) |
| Broad edge >=0.05, flat 1u | 201 | 76 | 125 | 37.8% | 201.00 | -7.78 | **-3.87%** | -24.62% | +144 | 162 / -3.52% | 39 / -5.30% |
| Locked quarterly selector | 94 | 42 | 52 | 44.7% | 65.96 | +12.31 | **+18.66%** | -16.24% | +116 | 84 / +20.17% | 10 / -0.97% |

## Corrected headline count: **3 of 5 strategies were profitable.**

(An earlier draft of this deliverable said "2 of 5" -- a hand-counting error in prose,
not a computed value; the underlying strategy-level numbers above were always correct.
This is now cross-checked automatically: `tests/test_v4_2025_2026_holdout_integrity.py`
fails the build if any document's stated profitable-strategy count disagrees with a
fresh count from `data/betting_results.csv`.)

Profitable: confidence/shrunk-Kelly (+9.25%), underdog edge (+5.74%), locked quarterly
selector (+18.66%). Not profitable: favorite edge (-5.17%), broad edge (-3.87%).

## Reading these numbers honestly

- **3 of 5 strategies are profitable** on this window, **2 of 5 are not**. This is a
  genuinely mixed result, shown in full rather than leading with only the winners.
- Sample sizes are small enough that most of these numbers carry real uncertainty:
  favorite edge is only 12 bets total (9 in 2025, 3 in 2026) -- not a reliable estimate
  in either direction. The 2026 breakdowns in particular (10, 4, 3, 39, and 10 bets
  respectively) are too thin to treat as separate, trustworthy year-level ROI figures;
  they are reported because the task asked for them, not because they are individually
  meaningful. They also all fall within the pre-March-2026 odds-coverage window (see
  `MODEL_VS_MARKET.md`), not the full 2026 test period.
- The locked quarterly selector's +18.66% ROI is the largest number here, but it comes
  from a strategy that was **freshly bootstrapped within this 19-month window**, not a
  literal continuation of the original 2018-2024 selector's internal state (see
  `METHODOLOGY.md` for why, and the relaxed 15-bet minimum-evidence bar used instead of
  the original's 50). Treat this number as a reasonable-effort reproduction of the
  *selection methodology*, not a bit-identical extension of the previously-published
  selector.
- **These are backtest ROI numbers on historical odds of unknown timing** (see
  `LIMITATIONS.md`, `odds_timing_status: "UNKNOWN"` in `resume_metrics_2026-08-18.json`).
  None of these numbers should be read as "this is what you would have won by actually
  betting in real time."
- Broad edge's -24.6% max drawdown on 201 bets is the most concerning single number in
  this table;
  this strategy is the least robust of the group.

## What this does and doesn't support

3 of 5 strategies (including the largest-sample fixed strategy, confidence/Kelly at 71
bets) were profitable on this specific ~15-month odds-matched window. This is disclosed
as a real, positive result for those three strategies specifically -- but given the
model itself lost decisively to the market on raw matched-subset accuracy
(`MODEL_VS_MARKET.md`), these positive betting results should be read as a property of
the *sizing/selection rules interacting with a small sample*, not as evidence the
underlying prediction model has a real edge over the market. ROI is deliberately
**not** used as a headline claim while the odds-timing convention remains unresolved.
