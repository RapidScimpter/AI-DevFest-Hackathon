"""Population Stability Index helpers used to detect changing attack behaviour."""
import numpy as np


def reference_bins(values, n=10):
    edges = np.unique(np.quantile(np.asarray(values, dtype=float), np.linspace(0, 1, n + 1)[1:-1]))
    return {'edges': edges.tolist(), 'share': _share(values, edges).tolist()}


def _share(values, edges):
    counts = np.bincount(np.searchsorted(edges, np.asarray(values, dtype=float), side='right'), minlength=len(edges) + 1)
    return (counts + .5) / (counts.sum() + .5 * len(counts))


def psi(reference, values):
    """PSI between a stored reference distribution and new values. >0.25 is a major shift."""
    ref = np.asarray(reference['share'])
    cur = _share(values, np.asarray(reference['edges']))
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def level(value):
    return 'major shift' if value >= .25 else 'moderate shift' if value >= .10 else 'stable'
