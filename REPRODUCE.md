# REPRODUCE.md - FundGenesis (ReflexMarket-AI)

## Prerequisites

- **Python**: 3.10+
- **OS**: Linux / macOS / Windows
- **GPU**: Not required

## Install

```bash
cd FundGenesis
pip install -r requirements.txt
```

Dependencies: numpy, matplotlib, fastapi, uvicorn

## Smoke Test

```bash
python -m pytest tests/ -v
```

Expected: Tests in `tests/test_agents.py`, `tests/test_models.py`, `tests/conftest.py` pass.

## Run Demo

```bash
python main.py
```

Or run the dashboard:

```bash
python dashboard/app.py
```

## Run Experiments

```bash
# Ablation study results already available in:
cat docs/demo_evidence_v0.2/ablation_results.csv
cat docs/demo_evidence_v0.2/ablation_summary.json
```

## Expected Outputs

- Demo narratives: `outputs/demo_narrative_reversal_result.json`, `outputs/demo_positive_narrative_result.json`, `outputs/demo_regulatory_shock_result.json`
- Ablation results: CSV and JSON in `docs/demo_evidence_v0.2/`
- Dashboard: Web UI for narrative-driven financial reflexivity simulation

## Known Issues

- No external data dependencies; uses synthetic/simulated data
- Dashboard requires browser access
- No hardcoded absolute paths detected in core code
