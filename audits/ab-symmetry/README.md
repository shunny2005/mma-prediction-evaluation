# A/B Symmetry Report

## The bug

The original model scored a matchup from a single feature row with one fighter in the
"A" slot. Symmetry was only encouraged through swapped-row data augmentation, so the
same two fighters could get materially different win probabilities depending on which
one was listed first (mean discrepancy 0.0357, max 0.3077 across the 2018-2025
walk-forward). A reported example showed 52.8% one way and an implied 25.7% the other.

## The fix

`score(A,B) = h(row_AB) - h(row_BA)`, `P(A beats B) = sigmoid(score(A,B))`, where `h` is a
single shared-weight network and `row_AB`/`row_BA` are the two orientations of the
matchup. This guarantees `score(A,B) = -score(B,A)` exactly, for any trained weights --
not a statistical tendency encouraged by data augmentation, an algebraic identity of the
model definition itself.

## Diagnostic method

For every one of the 4,108 walk-forward test predictions (2018-2025, locked model, real
out-of-sample fights), the model was run twice: once as trained (`P(A,B)`), and once on the
independently-reconstructed reversed-orientation row (`P(B,A)`, via a second, genuinely separate
forward pass, not by assuming `1-P(A,B)`). `implied_p_ab = 1 - P(B,A)`, `symmetry_error =
|P(A,B) - implied_p_ab|`. Full per-fight table: `symmetry/per_fight_symmetry.csv`.

## Results: 4,108 walk-forward matchups tested

| statistic | old model | new model |
| --- | ---: | ---: |
| Matchups tested | 4,114 | 4,108 |
| Mean symmetry error | 0.0357 | 0.0000000211 |
| Median symmetry error | 0.0267 | ~0.0 (5.6e-17) |
| P95 symmetry error | 0.0998 | 0.0000000700 |
| P99 symmetry error | 0.1433 | 0.0000001000 |
| Max symmetry error | 0.3077 | 0.0000001400 |
| Count > 1e-6 | 4,114 (100.0%) | 0 (0.0%) |
| Count > 1e-4 | 4,105 (99.8%) | 0 (0.0%) |
| Count > 1e-3 | 4,037 (98.1%) | 0 (0.0%) |
| Count > 1e-2 | 3,291 (80.0%) | 0 (0.0%) |
| Order-caused pick flips | not tracked (new diagnostic) | 0 |

The remaining ~1e-8 mean / ~1e-7 max error in the new model is float32 arithmetic noise,
not model-level asymmetry -- four to five orders of magnitude below the old model's mean
error, and below any threshold that could plausibly change a betting or accuracy decision.

"Order-caused pick flips" counts fights where the forward and reversed queries disagree about
which fighter is favored, excluding genuine exact 0.5/0.5 ties (which both orientations
correctly agree are a coin flip). 0 of 4,108.

These counts predate a later fighter-identity deduplication (4,088 predictions after it).
The symmetry guarantee does not depend on the data and was reconfirmed on the corrected
set.

## Explicit check: Mackenzie Dern vs. Gillian Robertson

Evaluated as a hypothetical matchup from each fighter's latest state, built two independent
ways -- Dern in slot A, then Robertson in slot A -- not one row algebraically inverted into
the other.

| | value |
| --- | ---: |
| P(Dern beats Robertson), Dern in slot A | 35.45% |
| P(Robertson beats Dern), Robertson in slot A | 64.55% |
| Sum | 100.00% (1.0 to float precision) |
| Symmetry error | 0.0 |

Full detail: `symmetry/dern_vs_robertson_check.csv`.

## Not averaged

`P(A,B)` and `P(B,A)` are computed by two independent forward passes of the same underlying
scorer, and the reported prediction (`P(A,B)`) is used as-is -- it is never averaged with
`1-P(B,A)`. Averaging the old model's two outputs would have hidden the asymmetry without
removing it. The two passes are reported here to show empirically that they already agree
to float precision without any averaging step.
