#!/usr/bin/env python3
"""
benchmarks/ablation_runner.py
================================
Ablation experiment runner.

Usage:
    python benchmarks/ablation_runner.py --output outputs/bench/ablation
"""

import sys
from pathlib import Path
import json
import csv
import numpy as np

project_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, project_root)

from reflexmarket.core.scenario_config import ScenarioConfig
from reflexmarket.core.simulation_runner import SimulationRunner

ABLATION_CONFIGS = ["full", "no_emotion", "no_kol", "no_regulation"]
ABLATION_DIR = Path(project_root) / "configs" / "ablations"
SEEDS = [0, 1, 2, 3, 4]


def run_ablation():
    results = []
    for config_name in ABLATION_CONFIGS:
        config_path = ABLATION_DIR / f"{config_name}.yaml"
        if not config_path.exists():
            print(f"  Skipping {config_name}: not found")
            continue
        for seed in SEEDS:
            config = ScenarioConfig.from_yaml(config_path)
            config.seed = seed
            runner = SimulationRunner(config)
            result = runner.run()
            result["ablation"] = config_name
            results.append(result)
            print(f"  {config_name} (seed={seed}): peak_bubble={result['peak_bubble_risk']:.3f}, "
                  f"bubble_hrs={result['bubble_high_risk_steps']}")

    # Save
    output_dir = Path("outputs/bench/ablation")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "ablation_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # CSV
    fields = ["ablation", "seed", "peak_bubble_risk", "bubble_high_risk_steps",
              "manipulation_high_risk_steps", "max_drawdown", "peak_price", "final_price"]
    with open(output_dir / "ablation_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    # Compute ablation comparison
    comparison = {}
    for ablation_name in ABLATION_CONFIGS:
        ablation_results = [r for r in results if r["ablation"] == ablation_name]
        if ablation_results:
            comparison[ablation_name] = {
                "peak_bubble_risk": float(np.mean([r["peak_bubble_risk"] for r in ablation_results])),
                "bubble_high_risk_steps": float(np.mean([r["bubble_high_risk_steps"] for r in ablation_results])),
                "n": len(ablation_results),
            }

    with open(output_dir / "ablation_comparison.json", "w") as f:
        json.dump(comparison, f, indent=2)

    # Print comparison
    print("\n" + "="*60)
    print("ABLATION COMPARISON")
    print("="*60)
    print(f"{'Ablation':<15} {'Peak Bubble Risk':>18} {'Bubble HRS':>12}")
    print("-"*45)
    for name, data in comparison.items():
        print(f"{name:<15} {data['peak_bubble_risk']:>18.3f} {data['bubble_high_risk_steps']:>12.1f}")

    return results


if __name__ == "__main__":
    run_ablation()
