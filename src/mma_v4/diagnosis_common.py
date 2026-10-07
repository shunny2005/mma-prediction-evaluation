"""Public subset of a private module: shared helpers only. The rest is withheld (see README)."""

from __future__ import annotations
import numpy as np


def paired_bootstrap_diff(
    y: np.ndarray, p_a: np.ndarray, p_b: np.ndarray, metric: str = "log_loss", n_boot: int = 2000, seed: int = 42
) -> dict:
    """Paired bootstrap comparison of two prediction vectors evaluated on the SAME fights.
    Returns the point difference (a - b) and a 95% CI on that difference so a numerically
    larger metric is never reported as "better" without an uncertainty estimate."""
    rng = np.random.default_rng(seed)
    n = len(y)
    eps = 1e-6
    pa = np.clip(p_a, eps, 1 - eps)
    pb = np.clip(p_b, eps, 1 - eps)

    def score(yy, pp):
        if metric == "log_loss":
            return -(yy * np.log(pp) + (1 - yy) * np.log(1 - pp))
        if metric == "brier_score":
            return (pp - yy) ** 2
        if metric == "accuracy":
            return ((pp >= 0.5).astype(float) == yy).astype(float)
        raise ValueError(metric)

    sa = score(y, pa)
    sb = score(y, pb)
    point_diff = float(sa.mean() - sb.mean())
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        diffs[i] = sa[idx].mean() - sb[idx].mean()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "metric": metric,
        "n": n,
        "point_diff_a_minus_b": point_diff,
        "ci_low_2_5pct": float(lo),
        "ci_high_97_5pct": float(hi),
        "statistically_distinguishable_95pct": bool(lo > 0 or hi < 0),
    }


def bootstrap_accuracy_ci(y: np.ndarray, p: np.ndarray, n_boot: int = 2000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    correct = (p >= 0.5).astype(float) == y
    n = len(y)
    accs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        accs[i] = correct[idx].mean()
    return {
        "n": n,
        "point_accuracy": float(correct.mean()),
        "ci_low_2_5pct": float(np.percentile(accs, 2.5)),
        "ci_high_97_5pct": float(np.percentile(accs, 97.5)),
        "std": float(accs.std()),
    }
