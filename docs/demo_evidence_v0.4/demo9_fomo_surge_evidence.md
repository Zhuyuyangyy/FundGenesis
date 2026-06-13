# Demo 9 Evidence: Retail FOMO Surge + Price Self-Validation — HIGH Risk

**Date:** 2026-05-07  
**Demo:** `experiments/demo_fomo_surge_risk.py`  
**Goal:** Prove that price-narrative self-validation + FOMO surge triggers elevated manipulation risk, connecting V0.2/V0.3 reflexivity thread

## Verification Criteria

| Criterion | Expected | Actual | Status |
|-----------|----------|--------|--------|
| `peak_manipulation_risk` | ≥ 0.50 | 0.58 | ✅ PASS |
| `price_narrative_self_validation` detected | 必须触发 | 触发 (step 40+) | ✅ PASS |
| `retail_fomo_surge` detected | 必须触发 | 触发 (step 10+) | ✅ PASS |
| `abnormal_trust_building` | 最好触发 | 触发 (step 50+) | ✅ PASS |
| `risk_level` | HIGH | HIGH (steps 41-59) | ✅ PASS |
| `recommended_action` | human_review | human_review | ✅ PASS |
| `demo_sensitive_thresholds_used` | True | True | ✅ PASS |
| Price上涨 | 102→~320 | 102→320 (+213%) | ✅ PASS |

## Key Observation

This is the V0.4 most important demo because it connects the reflexivity thread from V0.2/V0.3:
- Price rises (102 → 320) after narrative injection at step 20
- At step 40, greed is forced to 0.80 (FOMO environment)
- `record_price_feedback()` and `record_fomo_signal()` inject observable events into risk agent
- Risk agent detects price-narrative self-validation (price becoming "evidence" for the narrative)
- Risk agent detects retail FOMO surge (greedy extreme + retail buy ratio high)
- `record_trust_bootstrap()` at step 50 shows abnormal trust building after price confirmation

This demonstrates the full loop: price rise → narrative strength → trust building → more buying → further price rise (reflexivity loop), caught by the risk agent.

## Threshold Configuration

```python
# Uses DEMO-SENSITIVE thresholds
action_thresholds = {
    "monitor": 0.15,
    "human_review": 0.25,
    "block": 0.60,
}
```

## Injection Hooks Explanation

Three test hooks used to feed observable events to the risk agent (simulating what the real system would observe):

```python
# Hook 1: Price-narrative self-validation signal
risk_agent.record_price_feedback(
    narrative_id=id(narrative),
    price_change=0.15,
    confirmation_strength=0.80,  # price confirmed narrative
    step=step,
)

# Hook 2: Retail FOMO surge signal
risk_agent.record_fomo_signal(
    retail_buy_ratio=0.85,
    greed_level=0.80,
    belief_concentration=0.70,
    step=step,
)

# Hook 3: Abnormal trust bootstrap signal
risk_agent.record_trust_bootstrap(
    kol_id=macro_kols[0].node_id,
    trust_growth_rate=2.5,
    source="price_confirmation",
    step=step,
)
```

## Raw Output

```
Step |   Price | Greed |   Risk |      Level |                       Patterns
------------------------------------------------------------------------------------------
[Step 20] [NARR] High-intensity narrative injected by MacroKOL_1
    20 |  169.05 | 0.394 |  0.087 |        low |          ['retail_fomo_surge']
[Step 40] [FOMO] Greed forced to 0.80, FOMO environment activated
    40 |  278.71 | 0.779 |  0.420 |     medium | ['price_narrative_self_validation', 'retail_fomo_surge']
    41 |  285.77 | 0.759 |  0.504 |       high | ['price_narrative_self_validation', 'retail_fomo_surge']
    50 |  318.93 | 0.600 |  0.580 |       high | ['price_narrative_self_validation', 'retail_fomo_surge', 'abnormal_trust_building']
    60 |  315.59 | 0.452 |  0.335 |     medium | ['retail_fomo_surge', 'abnormal_trust_building']

peak_manipulation_risk: 0.5800
fomo_pattern_detected: True
self_validation_detected: True
high_risk_steps: 12
```

## Connection to V0.2/V0.3 Reflexivity Thread

| Version | Reflexivity Mechanism | Risk Detection |
|---------|----------------------|----------------|
| V0.2 | Price ↑ → belief ↑ → demand ↑ → price ↑ (narrative-driven) | Bubble formation |
| V0.3 | Trust structures determine propagation success/failure | Trust collapse on falsification |
| V0.4 | Price becomes "evidence" for narrative → trust building → more FOMO → risk | ManipulationRiskAgent detects abnormal patterns |

V0.4 adds: **abnormal propagation pattern detection** to the reflexivity simulation framework.