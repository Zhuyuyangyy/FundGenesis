import json

for name in ['baseline', 'light', 'strong']:
    d = json.load(open(f'outputs/demo_v0.5_{name}/result.json'))
    summary = d.get('intervention_summary', {})
    print(f'{name}:')
    print(f'  total_interventions: {summary.get("total_interventions", "N/A")}')
    print(f'  first_intervention_step: {summary.get("first_intervention_step", "N/A")}')
    print(f'  peak_bubble_risk: {d["peak_bubble_risk"]}')
    print(f'  peak_manipulation_risk: {d["peak_manipulation_risk"]}')
    print(f'  high_risk_steps: {d["high_risk_steps"]}')
    
    steps = d.get('steps', [])
    print(f'  steps type: {type(steps)} len={len(steps)}')
    if steps and isinstance(steps, list) and len(steps) > 0:
        first = steps[0]
        print(f'  first step type: {type(first)} val={first if not isinstance(first, dict) else list(first.keys())[:5]}')
        if isinstance(first, dict):
            ns_vals = [(s['step'], s.get('narrative_strength', 'N/A')) for s in steps[:10] if 'narrative_strength' in s]
            print(f'  first 10 ns: {ns_vals}')
    print()