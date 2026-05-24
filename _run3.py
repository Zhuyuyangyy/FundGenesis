"""Quick test of bubble_risk with fixed KOL belief propagation across 3 demos"""
import subprocess, json, sys, os

os.chdir(r"D:\ZYY Project\FundGenesis")

results = {}
for name, script in [
    ("Baseline", "experiments/demo_regulation_baseline.py"),
    ("Light", "experiments/demo_regulation_light.py"),
    ("Strong", "experiments/demo_regulation_strong.py"),
]:
    print(f"\n{'='*60}\nRunning {name}...\n{'='*60}")
    r = subprocess.run(
        ["python", script],
        capture_output=True, text=True, timeout=300,
        cwd=r"D:\ZYY Project\FundGenesis"
    )
    # Print last 20 lines of output
    lines = (r.stdout + r.stderr).split("\n")
    for line in lines[-25:]:
        if line.strip():
            print(line)
    
    # Load result
    result_path = f"outputs/demo_v0.5_{name.lower()}/result.json"
    if os.path.exists(result_path):
        with open(result_path) as f:
            d = json.load(f)
        results[name] = {
            "peak_bubble": d["peak_bubble_risk"],
            "peak_manip": d["peak_manipulation_risk"],
            "high_risk_steps": d["high_risk_steps"],
            "interventions": d.get("total_interventions", 0),
            "first_intervention": d.get("first_intervention_step", "N/A"),
        }
    else:
        print(f"  [WARNING] result.json not found at {result_path}")

print("\n\n" + "="*70)
print("COMPARISON — bubble_risk with fixed KOL belief (0.1 → 1.0)")
print("="*70)
print(f"{'Group':<12} {'peak_manip':>12} {'peak_bubble':>14} {'high_risk':>12} {'interventions':>14} {'first_int':>12}")
print("-"*70)
for name, r in results.items():
    print(f"{name:<12} {r['peak_manip']:>12.4f} {r['peak_bubble']:>14.4f} {r['high_risk_steps']:>12} {r['interventions']:>14} {str(r['first_intervention']):>12}")