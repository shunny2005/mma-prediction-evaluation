# Locked MMA Betting Strategy

This is the frozen validation specification. Do not use these results to keep tuning thresholds, candidate rules, score weights, selection cadence, or staking settings.

## Locked Primary Strategy

- Primary selector: `quarterly__min_bets_50__min_windows_5__default_during_burnin`.
- Selection updates quarterly.
- At the start of each quarter, the selector scores candidate betting rules using only data strictly before that quarter.
- Candidate selection requires at least 50 historical bets and at least 5 historical windows.
- Burn-in uses the default rule when needed, but the headline metric is post-burn-in only.
- Headline result scope: `excluding_burnin`.

Quarterly was chosen instead of card-by-card because it is less reactive and less likely to chase short-term noise, while still retaining the best slower-update historical profile from the rolling experiment.

## Historical Reference

- Locked quarterly excluding burn-in: 1058 bets, 1.68 units P/L, 0.78% ROI, -3.54% max drawdown.
- Full period including burn-in: 1232 bets, -17.41 units P/L, -4.48% ROI.
- Burn-in only: 174 bets, -19.09 units P/L, -10.97% ROI.

## Frozen Benchmarks

| strategy_name | bets | profit_loss | roi | max_drawdown | favorite_roi | underdog_roi |
| --- | --- | --- | --- | --- | --- | --- |
| confidence_ge_0.6__shrunk_kelly_s0.5_k0.25_cap_0.5pct | 224 | -6.94406 | -0.068654 | -0.133185 | 0.04451 | -0.11761 |
| underdog_edge_ge_0.03_conf_ge_0.55_cap_plus_150__bankroll_0.25pct | 158 | -0.33709 | -0.008415 | -0.03948 | 0.0 | -0.008415 |
| favorite_edge_ge_0.075_conf_ge_0.65__bankroll_0.25pct | 57 | -1.218664 | -0.086562 | -0.020431 | -0.086562 | 0.0 |
| edge_ge_0.05__flat_1u | 753 | -46.280307 | -0.061461 | -0.568363 | 0.003901 | -0.074099 |

## Required Interpretation

1. Locked strategy: quarterly selector with 50 minimum historical bets, 5 minimum historical windows, and default during burn-in.
2. Quarterly was selected because it is a slower, more realistic cadence than card-by-card and had strong post-burn-in historical performance.
3. Burn-in is excluded from the headline because those bets were not selected from enough prior strategy evidence.
4. Historical reference carried forward: 1.68 units P/L, 0.78% ROI, and -3.54% max drawdown after burn-in.
5. Fixed benchmarks tracked: confidence shrunk Kelly, capped underdog, favorite edge, and edge >= 0.05 flat 1u.
6. Future success: positive post-lock ROI after a meaningful bet count, controlled drawdown ideally under 10%, no dependence on one outlier win, and competitive results versus fixed baselines.
7. Future failure: negative ROI over a meaningful sample, drawdown materially worse than history, dependence on one outlier, consistent benchmark outperformance, or unstable selected rules.
8. Do not change candidate rules, thresholds, score formula, selection cadence, burn-in policy, minimum bet/window thresholds, sizing rules, favorite/underdog definitions, or edge calculations.