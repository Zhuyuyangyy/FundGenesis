import json, os
os.chdir(r"D:\ZYY Project\FundGenesis")
for name, subdir in [("Baseline", "demo_v0.5_baseline"), ("Light", "demo_v0.5_light"), ("Strong", "demo_v0.5_strong")]:
    path = f"outputs/{subdir}/result.json"
    with open(path) as f:
        d = json.load(f)
    print(f"\n{name}: keys={list(d.keys())}")
    print(f"  total_interventions={d.get('total_interventions','MISSING')}")
    print(f"  first_intervention={d.get('first_intervention_step','MISSING')}")