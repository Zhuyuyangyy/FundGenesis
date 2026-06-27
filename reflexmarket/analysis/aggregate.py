"""
reflexmarket/analysis/aggregate.py
=====================================
Aggregate benchmark results by scenario and category.
"""

import csv
import json
import numpy as np
from collections import defaultdict
from pathlib import Path


def load_csv(path: str) -> list[dict]:
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def aggregate(summary_csv: str, output_json: str):
    rows = load_csv(summary_csv)
    metrics = ["peak_bubble_risk", "bubble_high_risk_steps", "max_drawdown",
               "manipulation_high_risk_steps", "overall_high_risk_steps", "intervention_count",
               "peak_price", "final_price"]

    by_scenario = defaultdict(list)
    by_category = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario_id"]].append(row)
        by_category[row.get("category", "unknown")].append(row)

    results = {"by_scenario": {}, "by_category": {}, "overall": {}}

    for scenario_id, scenario_rows in by_scenario.items():
        results["by_scenario"][scenario_id] = {
            "total": len(scenario_rows),
            "passed": sum(1 for r in scenario_rows if r.get("passed") == "True" or r.get("passed") == True),
        }
        for metric in metrics:
            values = []
            for row in scenario_rows:
                try: values.append(float(row.get(metric, 0)))
                except: pass
            if values:
                results["by_scenario"][scenario_id][metric] = {
                    "mean": float(np.mean(values)), "std": float(np.std(values)),
                    "min": float(np.min(values)), "max": float(np.max(values)), "n": len(values),
                }

    for category, cat_rows in by_category.items():
        results["by_category"][category] = {"total": len(cat_rows)}
        for metric in metrics:
            values = []
            for row in cat_rows:
                try: values.append(float(row.get(metric, 0)))
                except: pass
            if values:
                results["by_category"][category][metric] = {
                    "mean": float(np.mean(values)), "std": float(np.std(values)), "n": len(values),
                }

    # Overall pass rate
    total = len(rows)
    passed = sum(1 for r in rows if r.get("passed") == "True" or r.get("passed") == True)
    results["overall"] = {"total_runs": total, "passed": passed, "pass_rate": passed / max(total, 1)}

    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    return results
