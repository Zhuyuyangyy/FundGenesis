import json, os
os.chdir(r"D:\ZYY Project\FundGenesis")

for name, subdir in [("Baseline", "demo_v0.5_baseline"), ("Light", "demo_v0.5_light"), ("Strong", "demo_v0.5_strong")]:
    path = f"outputs/{subdir}/result.json"
    with open(path) as f:
        d = json.load(f)
    
    print(f"\n{'='*50}\n{name}\n{'='*50}")
    for k, v in d.items():
        if k == "verification":
            print(f"  {k}: [nested verification]")
            continue
        if k == "intervention_summary":
            print(f"  {k}:")
            for ik, iv in v.items():
                print(f"    {ik}: {iv}")
            continue
        print(f"  {k}: {v}")