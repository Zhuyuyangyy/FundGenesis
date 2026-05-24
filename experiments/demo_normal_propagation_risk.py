"""
experiments/demo_normal_propagation_risk.py
==========================================
Demo 7: Normal Narrative Propagation — No High Risk

V0.4 ManipulationRiskAgent — Demo 7

核心论点：
  正常叙事情境下（单一 KOL 正常传播，无协同放大，
  价格变动与叙事方向一致但速度正常），manipulation_risk_score
  应该保持在 LOW 水平，不触发人工复核。

实验设计：
  1. 初始化完整市场（Narrative + KOL + Trust + Reflexivity）
  2. Step 30：单一 Influencer 注入普通正向叙事
  3. 运行 200 步，持续追踪 manipulation_risk_score
  4. 验证：manipulation_risk_score < 0.30（应为 LOW）

成功标准：
  - manipulation_risk_score < 0.30 全程
  - 无任何 HIGH/CRITICAL 模式触发
  - recommended_action == "allow"
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.creator_controller import CreatorController, MarketConfig
from core.emotion_field import EmotionField
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from risk.manipulation_risk_agent import ManipulationRiskAgent, RiskLevel


def run_demo_normal_propagation_risk(output_dir: str = None, steps: int = 200):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.4_normal_propagation"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 7: Normal Narrative Propagation — No High Risk")
    print("=" * 60)

    # ── 市场环境 ─────────────────────────────────────────
    controller = CreatorController(
        market_config=MarketConfig(
            initial_price=100.0,
            impact_coefficient=0.20,
            noise_std=0.008,
            total_agents=100,
        ),
        emotion_config={
            "initial_fear": 0.15,
            "initial_greed": 0.55,
            "fear_inertia": 0.92,
            "greed_inertia": 0.92,
        }
    )
    market = controller.setup_market()
    emotion = controller.setup_emotion()
    belief_updater = BeliefUpdaterV2()

    # ── KOL Network ──────────────────────────────────────
    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )

    # ── Narrative Engine ─────────────────────────────────
    narrative_engine = NarrativeEngine()

    # ── Propagation Model ─────────────────────────────────
    propagation = PropagationModel(kol_network)

    # ── Trust Engine ─────────────────────────────────────
    trust_config = TrustConfig()
    trust_engine = TrustEngine(trust_config)
    bootstrapper = TrustBootstrapper()
    bootstrapper.bootstrap_network(kol_network, trust_engine)

    # ── Reflexivity Monitor ──────────────────────────────
    reflexivity_monitor = ReflexivityMonitor()

    # Manipulation Risk Agent（生产默认阈值，全程应保持 LOW）
    risk_agent = ManipulationRiskAgent()

    # 验证默认阈值未被修改
    assert risk_agent.action_thresholds == ManipulationRiskAgent.DEFAULT_ACTION_THRESHOLDS

    # ── Agents ────────────────────────────────────────────
    from agents.emotional_retail import EmotionalRetailAgent
    from agents.trend_follower import TrendFollowerAgent
    from agents.value_investor import ValueInvestorAgent

    agents = []
    for i in range(100):
        if i < 10:
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        elif i < 40:
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        else:
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

    # ── Injection：单一 Influencer 正常叙事 ──────────────
    def inject_normal_narrative(step):
        if step == 30:
            influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
            if influencer_kols:
                influencer = influencer_kols[0]
                narrative = NarrativeEvent(
                    name="行业基本面持续改善，企业盈利预期良好",
                    category=NarrativeCategory.EARNINGS,
                    polarity=Polarity.POSITIVE,
                    target_sector="general",
                    intensity=0.65,
                    credibility=0.70,
                    novelty=0.50,
                    duration=50,
                    source=influencer.node_id,
                )
                narrative_engine.inject(narrative)
                propagation.inject_narrative(narrative)
                print(f"[Step {step}] [NARR] Normal narrative injected by {influencer.name}")
                return True
        return False

    # ── 主循环 ────────────────────────────────────────────
    print(f"\n{'Step':>6} | {'Price':>7} | {'Risk':>6} | {'Level':>10} | {'Patterns':>20} | {'Action':>12}")
    print("-" * 85)

    risk_log = []
    high_risk_steps = 0
    peak_risk_action = "allow"

    for step in range(steps):
        # Narrative 注入
        inject_normal_narrative(step)

        # 传播 tick
        propagation.step()
        narrative_engine.tick()

        # Belief Update
        belief_updater.update_all(
            agents=agents,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=narrative_engine,
        )

        # Emotion from narrative
        price_change = market.price_change_pct if market.price_history else 0.0
        narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)

        # Agent Trading
        for agent in agents:
            action = agent.decide(market.get_snapshot(), emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)

        # Price Update
        market.update_price(emotion)

        # Emotion Decay
        emotion.decay_toward_neutral(inertia=0.92)

        # Reflexivity 监控
        metrics = reflexivity_monitor.observe(
            step=step,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=narrative_engine,
            agents=agents,
        )

        # Manipulation Risk 评估
        risk_report = risk_agent.evaluate(
            step=step,
            kol_network=kol_network,
            trust_engine=trust_engine,
            reflexivity_monitor=reflexivity_monitor,
            market=market,
            narrative_engine=narrative_engine,
            propagation_model=propagation,
            agents=agents,
        )

        risk_log.append(risk_report.as_dict())
        if risk_report.manipulation_risk_score >= max(risk_agent.risk_history[:-1] + [0]) if risk_agent.risk_history else True:
            peak_risk_action = risk_report.recommended_action

        if step % 30 == 0 or risk_report.risk_level.value in ("high", "critical"):
            patterns = [p.pattern.value for p in risk_report.detected_patterns]
            print(
                f"{step:>6} | {market.price:>7.2f} | "
                f"{risk_report.manipulation_risk_score:>6.3f} | "
                f"{risk_report.risk_level.value:>10} | "
                f"{str(patterns[:2]):>20} | "
                f"{risk_report.recommended_action:>12}"
            )

        if risk_report.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            high_risk_steps += 1

    # ── 结果摘要 ─────────────────────────────────────────
    max_risk = max(risk_agent.risk_history) if risk_agent.risk_history else 0.0
    avg_risk = sum(risk_agent.risk_history) / len(risk_agent.risk_history) if risk_agent.risk_history else 0.0

    result = {
        "demo": "normal_propagation_no_high_risk",
        "v0.4_risk_agent": True,
        "description": "Normal single-KOL narrative should stay LOW risk",
        "steps": steps,
        "max_manipulation_risk": round(max_risk, 4),
        "avg_manipulation_risk": round(avg_risk, 4),
        "high_risk_steps": high_risk_steps,
        "final_price": round(market.price, 2),
        "price_change_pct": round((market.price - 100.0) / 100.0, 4),
        "risk_history": [round(r, 4) for r in risk_agent.risk_history],
        "regime_summary": reflexivity_monitor.regime_summary(),
        "verification": {
            "risk_stayed_low": max_risk < 0.30,
            "no_high_risk_steps": high_risk_steps == 0,
            "default_thresholds_used": risk_agent.action_thresholds == ManipulationRiskAgent.DEFAULT_ACTION_THRESHOLDS,
        }
    }

    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    print(f"  demo: {result['demo']}")
    print(f"  max_manipulation_risk: {max_risk:.4f} (threshold < 0.30)")
    print(f"  avg_manipulation_risk: {avg_risk:.4f}")
    print(f"  high_risk_steps: {high_risk_steps} (expected: 0)")
    print(f"  default_thresholds_used: {risk_agent.action_thresholds == ManipulationRiskAgent.DEFAULT_ACTION_THRESHOLDS}")
    all_pass = all(result["verification"].values())
    print(f"\n  {'PASS' if all_pass else 'FAIL'}: "
          f"Normal narrative propagation risk {'stays LOW' if all_pass else 'exceeded threshold'}")
    print(f"\n  Results saved to: {output_dir}/")
    return result


if __name__ == "__main__":
    run_demo_normal_propagation_risk()
