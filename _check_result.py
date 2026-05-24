import json, os

os.chdir(r"D:\ZYY Project\FundGenesis")

path = "outputs/demo_v0.5_baseline/result.json"
with open(path) as f:
    d = json.load(f)

print("All keys:", list(d.keys()))
for k, v in d.items():
    vtype = type(v).__name__
    if vtype in ("list", "dict"):
        print(f"  {k}: {vtype} (len={len(v)})")
    elif vtype in ("int", "float", "str"):
        print(f"  {k}: {vtype} = {v}")

# Check for any csv or other log files
output_dir = "outputs/demo_v0.5_baseline"
print("\nFiles in output_dir:")
for f in os.listdir(output_dir):
    fpath = os.path.join(output_dir, f)
    size = os.path.getsize(fpath)
    print(f"  {f}: {size} bytes")