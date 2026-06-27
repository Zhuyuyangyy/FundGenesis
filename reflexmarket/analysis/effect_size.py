"""
reflexmarket/analysis/effect_size.py
======================================
Cohen's d effect size for regulation comparison.
"""

import numpy as np
from typing import Optional


def cohens_d(group1: list[float], group2: list[float]) -> Optional[dict]:
    if len(group1) < 2 or len(group2) < 2:
        return None
    n1, n2 = len(group1), len(group2)
    m1, m2 = np.mean(group1), np.mean(group2)
    s1, s2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return {"d": 0.0, "interpretation": "undefined", "mean_diff": float(m1 - m2)}
    d = (m1 - m2) / pooled_std
    if abs(d) < 0.2:
        interp = "negligible"
    elif abs(d) < 0.5:
        interp = "small"
    elif abs(d) < 0.8:
        interp = "medium"
    else:
        interp = "large"
    return {"d": float(d), "interpretation": interp, "mean1": float(m1), "mean2": float(m2),
            "mean_diff": float(m1 - m2), "n1": n1, "n2": n2}
