"""
reflexmarket/analysis/compare_conditions.py
===============================================
Compare regulation conditions (baseline vs light vs strong).

Usage:
    python -m reflexmarket.analysis.compare_conditions --input summary.csv --output regulation_comparison.json
"""

import argparse
import csv
import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from reflexmarket.analysis.effect_size import cohens_d


def load_csv(path: str) -> list[dict]:
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def compare_conditions(summary_csv: str, output_json: str):
    rows = load_csv(summary_csv)
    metrics = ["peak_bubble_risk", "bubble_high_risk_steps", "max_drawdown",
               "overall_high_risk_steps", "intervention_count"]

    by_condition = defaultdict(lambda: defaultdict(list))
    for row in rows:
        cond = row.get("condition", "default")
        for metric in metrics:
            try:
                by_condition[cond][metric].append(float(row.get(metric, 0)))
            except (ValueError, TypeError):
                pass

    conditions = sorted(by_condition.keys())
    results = {"conditions": conditions, "metrics": {}, "pairwise": {}}

    for metric in metrics:
        results["metrics"][metric] = {}
        for cond in conditions:
            vals = by_condition[cond][metric]
            if vals:
                results["metrics"][metric][cond] = {
                    "mean": float(np.mean(vals)),
                    "std": float(np.std(vals)),
                    "n": len(vals),
                }

    # Pairwise comparisons
    pairs = [("baseline", "light"), ("baseline", "strong"), ("light", "strong")]
    for c1, c2 in pairs:
        if c1 in by_condition and c2 in by_condition:
            pair_key = f"{c1}_vs_{c2}"
            results["pairwise"][pair_key] = {}
            for metric in metrics:
                g1 = by_condition[c1][metric]
                g2 = by_condition[c2][metric]
                es = cohens_d(g1, g2)
                if es:
                    results["pairwise"][pair_key][metric] = es

    # Generate regulation table markdown
    table_lines = []
    table_lines.append("| Condition | Peak Bubble Risk | Bubble High-Risk Steps | Max Drawdown | Interventions |")
    table_lines.append("|-----------|----------------:|-----------------------:|-------------:|--------------:|")
    for cond in conditions:
        m = results["metrics"]
        pbr = m.get("peak_bubble_risk", {}).get(cond, {})
        bhrs = m.get("bubble_high_risk_steps", {}).get(cond, {})
        md = m.get("max_drawdown", {}).get(cond, {})
        ic = m.get("intervention_count", {}).get(cond, {})
        table_lines.append(
            f"| {cond.capitalize():9} | {pbr.get('mean', 0):.3f} ± {pbr.get('std', 0):.3f} "
            f"| {bhrs.get('mean', 0):.1f} ± {bhrs.get('std', 0):.1f} "
            f"| {md.get('mean', 0):.2f} ± {md.get('std', 0):.2f} "
            f"| {ic.get('mean', 0):.1f} ± {ic.get('std', 0):.1f} |"
        )
    results["regulation_table_md"] = "\n".join(table_lines)

    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)

    # Also save regulation_table.md
    table_path = Path(output_json).parent / "regulation_table.md"
    with open(table_path, "w") as f:
        f.write("# Regulation Comparison Table\n\n")
        f.write(results["regulation_table_md"])
        f.write("\n\n## Pairwise Effect Sizes (Cohen's d)\n\n")
        for pair_key, pair_metrics in results["pairwise"].items():
            f.write(f"### {pair_key}\n\n")
            f.write("| Metric | Cohen's d | Interpretation |\n")
            f.write("|--------|----------:|---------------|\n")
            for metric, es in pair_metrics.items():
                f.write(f"| {metric} | {es['d']:.3f} | {es['interpretation']} |\n")
            f.write("\n")

    print(f"Regulation comparison saved to: {output_json}")
    print(f"Regulation table saved to: {table_path}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    compare_conditions(args.input, args.output)


if __name__ == "__main__":
    main()
