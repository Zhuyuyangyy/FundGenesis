"""
reflexmarket/analysis/bootstrap.py
=====================================
Bootstrap confidence intervals for benchmark metrics.

Usage:
    python -m reflexmarket.analysis.bootstrap --input summary.csv --output bootstrap_ci.json
"""

import argparse
import csv
import json
import numpy as np
from pathlib import Path
from collections import defaultdict


def load_csv(path: str) -> list[dict]:
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def bootstrap_ci(values: list[float], n_bootstrap: int = 1000, ci: float = 0.95) -> dict:
    arr = np.array(values)
    if len(arr) < 2:
        return {"mean": float(np.mean(arr)) if len(arr) > 0 else 0.0,
                "ci_lower": 0.0, "ci_upper": 0.0, "n": len(arr)}

    boot_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(arr, size=len(arr), replace=True)
        boot_means.append(float(np.mean(sample)))

    alpha = (1 - ci) / 2
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "ci_lower": float(np.percentile(boot_means, alpha * 100)),
        "ci_upper": float(np.percentile(boot_means, (1 - alpha) * 100)),
        "n": len(arr),
    }


def compute_bootstrap(summary_csv: str, output_json: str):
    rows = load_csv(summary_csv)
    metrics = ["peak_bubble_risk", "bubble_high_risk_steps", "max_drawdown",
               "manipulation_high_risk_steps", "overall_high_risk_steps", "intervention_count"]

    results = {}
    by_scenario = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario_id"]].append(row)

    for scenario_id, scenario_rows in by_scenario.items():
        results[scenario_id] = {}
        for metric in metrics:
            values = []
            for row in scenario_rows:
                try:
                    values.append(float(row.get(metric, 0)))
                except (ValueError, TypeError):
                    pass
            if values:
                results[scenario_id][metric] = bootstrap_ci(values)

    # Also compute per-condition aggregation
    by_condition = defaultdict(list)
    for row in rows:
        cond = row.get("condition", "default")
        by_condition[cond].append(row)

    results["_by_condition"] = {}
    for cond, cond_rows in by_condition.items():
        results["_by_condition"][cond] = {}
        for metric in metrics:
            values = []
            for row in cond_rows:
                try:
                    values.append(float(row.get(metric, 0)))
                except (ValueError, TypeError):
                    pass
            if values:
                results["_by_condition"][cond][metric] = bootstrap_ci(values)

    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Bootstrap CI saved to: {output_json}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to summary.csv")
    parser.add_argument("--output", required=True, help="Path to output bootstrap_ci.json")
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    args = parser.parse_args()
    compute_bootstrap(args.input, args.output)


if __name__ == "__main__":
    main()
