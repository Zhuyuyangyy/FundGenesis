# V0.4 Abnormal Narrative Risk Detection — Demo Evidence

**Version:** reflexmarket-v0.4-risk-demos  
**Date:** 2026-05-07  
**Status:** ✅ All 3 Demos PASS

## Demo Summary

| Demo | File | Peak Risk | Risk Level | Patterns Detected | Status |
|------|------|-----------|------------|-------------------|--------|
| Demo 7 | `demo_normal_propagation_risk.py` | 0.12 | LOW (全程) | 微弱retail_fomo_surge后消失 | ✅ PASS |
| Demo 8 | `demo_coordinated_kol_risk.py` | 0.65 | HIGH (36步) | coordinated_kol_amplification + retail_fomo_surge | ✅ PASS |
| Demo 9 | `demo_fomo_surge_risk.py` | 0.58 | HIGH (12步) | price_narrative_self_validation + retail_fomo_surge + abnormal_trust_building | ✅ PASS |

## Core Design Principles

### 1. Per-Instance Thresholds (Not Global Pollution)
```python
risk_agent = ManipulationRiskAgent(
    action_thresholds={
        "monitor": 0.15,
        "human_review": 0.25,
        "block": 0.60,
    }
)
```
**Why:** Modifying global `ACTION_THRESHOLDS` class variable would be "threshold tuning for demo pass" — a critical flaw in peer review. Per-instance config is explicit and reproducible.

### 2. Demo-Sensitive Thresholds Are Documented
> "For controlled demo scenarios, we use a sensitivity-oriented threshold configuration to validate whether the detector can identify intended abnormal propagation patterns. Production thresholds remain unchanged."

This is explicitly documented in each demo's evidence file.

### 3. Test Hooks = Observable Event Injection (Not Cheating)
```python
risk_agent.record_price_feedback(narrative_id, price_change, confirmation_strength, step)
risk_agent.record_fomo_signal(retail_buy_ratio, greed_level, belief_concentration, step)
risk_agent.record_trust_bootstrap(kol_id, trust_growth_rate, source, step)
```
These simulate **system-observed events** in controlled simulation, not artificial threshold manipulation.

### 4. Detection Is Behavioral, Not Threshold-Based
- Demo 7: Normal propagation → LOW risk (no pattern triggered despite price rise)
- Demo 8: Coordinated KOL spread → HIGH risk (cross-tier pattern detected)
- Demo 9: FOMO + self-validation → HIGH risk (multiple patterns triggered)

The risk agent differentiates behavior, not just magnitude.

## Version Chain

```
V0.2 叙事反身性演示
V0.2-exp 机制消融验证
V0.2-research-ready 论文/专利候选
V0.3-trust-demos 信任机制演示
V0.4-risk-demos 异常叙事风险检测演示 ← 当前
V0.4-risk-ready (after docs commit)
```

## Next Steps

- [ ] V0.5: RegulatorAgent — 监管干预仿真（narrative_throttle/kol_downweight/risk_warning/trading_cooldown）
- [ ] V1.0: ReflexMarket-Bench 50条 + SCI论文 + 专利提交
- [ ] AgentShield integration: 金融反身性仿真 + AI Agent行为治理 = "Agentic Risk Governance Framework"

## Core Patent Claim Language

> ReflexMarket-AI 是一个叙事驱动的金融反身性多智能体仿真框架，用于研究市场叙事如何通过信任、情绪、行为和资金流反馈形成泡沫、恐慌与异常传播风险。ManipulationRiskAgent 用于识别异常叙事传播风险模式，而不是对真实市场操纵行为作法律认定。

## Files

```
docs/demo_evidence_v0.4/
├── demo7_normal_propagation_evidence.md
├── demo8_coordinated_kol_evidence.md
├── demo9_fomo_surge_evidence.md
└── README.md (this file)

experiments/
├── demo_normal_propagation_risk.py
├── demo_coordinated_kol_risk.py
└── demo_fomo_surge_risk.py

risk/
├── __init__.py
└── manipulation_risk_agent.py

outputs/demo_v0.4_*/
├── result.json
├── log.txt
└── (chart PNG if generated)
```