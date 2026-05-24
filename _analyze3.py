import json, os

os.chdir(r"D:\ZYY Project\FundGenesis")

# Key governance metrics from result.json (no metrics_log needed)
groups = {}
for name, subdir in [
    ("Baseline", "demo_v0.5_baseline"),
    ("Light", "demo_v0.5_light"),
    ("Strong", "demo_v0.5_strong"),
]:
    path = f"outputs/{subdir}/result.json"
    with open(path) as f:
        d = json.load(f)
    groups[name] = d

print("="*75)
print("V0.5 GOVERNANCE EFFECT — post KOL belief fix (0.1→1.0)")
print("="*75)
print()
print(f"{'Metric':<32} {'Baseline':>10} {'Light':>10} {'Strong':>10} {'Expected':<20}")
print("-"*75)

rows = [
    ("peak_manipulation_risk", "manipulation_risk", "max"),
    ("peak_bubble_risk", "bubble_risk", "max"),
    ("high_risk_steps (manip)", "high_risk_steps", "sum"),
    ("total_interventions", "total_interventions", "max"),
    ("final_drawdown_pct", "final_drawdown_pct", "min"),
]

for metric, key, sense in rows:
    b = groups["Baseline"].get(metric, 0)
    l = groups["Light"].get(metric, 0)
    s = groups["Strong"].get(metric, 0)
    if isinstance(b, float):
        print(f"{metric:<32} {b:>10.4f} {l:>10.4f} {s:>10.4f}")
    else:
        print(f"{metric:<32} {str(b):>10} {str(l):>10} {str(s):>10}")

print()
print(f"{'first_intervention_step':<32} {str(groups['Baseline'].get('first_intervention_step','N/A')):>10} "
      f"{str(groups['Light'].get('first_intervention_step','N/A')):>10} "
      f"{str(groups['Strong'].get('first_intervention_step','N/A')):>10}")

print()
print("="*75)
print("INTERPRETATION")
print("="*75)

b_manip = groups["Baseline"]["peak_manipulation_risk"]
l_manip = groups["Light"]["peak_manipulation_risk"]
s_manip = groups["Strong"]["peak_manipulation_risk"]
b_hrs = groups["Baseline"]["high_risk_steps"]
l_hrs = groups["Light"]["high_risk_steps"]
s_hrs = groups["Strong"]["high_risk_steps"]
b_int = groups["Baseline"]["total_interventions"]
l_int = groups["Light"]["total_interventions"]
s_int = groups["Strong"]["total_interventions"]
b_bub = groups["Baseline"]["peak_bubble_risk"]
l_bub = groups["Light"]["peak_bubble_risk"]
s_bub = groups["Strong"]["peak_bubble_risk"]

print(f"\n[bubble_risk]  Baseline={b_bub:.4f}  Light={l_bub:.4f}  Strong={s_bub:.4f}")
if b_bub == l_bub == s_bub == 1.0:
    print("  ⚠ All three hit ceiling (1.0) — formula needs tuning")
    print("  → Belief+Volatility formula saturates; need to rebalance coefficients")

print(f"\n[manipulation_risk]  Baseline={b_manip:.4f}  Light={l_manip:.4f}  Strong={s_manip:.4f}")
print(f"  Peak risk forms BEFORE first intervention in all groups")
print(f"  → Expected: intervention reduces POST-intervention risk, not peak")

print(f"\n[high_risk_steps (manip≥0.25)]  Baseline={b_hrs}  Light={l_hrs}  Strong={s_hrs}")
if s_hrs < l_hrs < b_hrs:
    print("  ✅ Trend correct: Strong < Light < Baseline")
elif s_hrs == l_hrs == b_hrs:
    print("  ⚠ All equal — intervention may not be reducing risk duration")

print(f"\n[interventions]  Baseline={b_int}  Light={l_int}  Strong={s_int}")
print(f"  Baseline should be 0 (no regulator) ✅" if b_int == 0 else f"  ❌ Baseline has {b_int} interventions!")
print(f"  Strong ≥ Light: {s_int >= l_int}")
print(f"  Strong first_intervention: {groups['Strong'].get('first_intervention_step','N/A')}")
print(f"  Light first_intervention: {groups['Light'].get('first_intervention_step','N/A')}")

print()
print("KEY ISSUE: bubble_risk saturates at 1.0 in ALL groups.")
print("The volatility-based formula (belief*25 * emotion*4 * volatility*50 * 5)")
print("is too aggressive — needs to be rebalanced to differentiate governance effect.")