"""
experiments/demo_coordinated_kol_risk.py
=========================================
Demo 8: Coordinated KOL Amplification — HIGH Risk

V0.4 ManipulationRiskAgent — Demo 8

核心论点：
  多 KOL（Macro + Influencer + Micro）在短时间窗口内协同放大同一叙事
  -> manipulation_risk_score 快速上升 -> 触发 HIGH risk

实验设计：
  1. 初始化完整市场
  2. Step 30：Macro KOL 注入高强度叙事
  3. Step 32-35：Influencer 接力传播（同一叙事）
  4. Step 36-40：Micro KOL 再次接力（跨层级协同）
  5. 验证：manipulation_risk_score >= 0.50（HIGH）
  6. 验证：detected_patterns 包含 "coordinated_kol_amplification"

成功标准：
  - manipulation_risk_score >= 0.50（HIGH）
  - detected_patterns 包含 "coordinated_kol_amplification"
  - recommended_action == "human_review" 或 "block"
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.creator_controller import CreatorController, MarketConfig
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from risk.manipulation_risk_agent import ManipulationRiskAgent, RiskLevel


def run_demo_coordinated_kol_risk(output_dir: str = None, steps: int = 200):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.4_coordinated_kol"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 8: Coordinated KOL Amplification — HIGH Risk")
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

    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )
    narrative_engine = NarrativeEngine()
    propagation = PropagationModel(kol_network)

    trust_config = TrustConfig()
    trust_engine = TrustEngine(trust_config)
    bootstrapper = TrustBootstrapper()
    bootstrapper.bootstrap_network(kol_network, trust_engine)

    reflexivity_monitor = ReflexivityMonitor()
    # Manipulation Risk Agent（demo-sensitive 阈值，用于验证检测能力）
    # 注意：这是受控实验配置，不修改默认生产阈值
    risk_agent = ManipulationRiskAgent(
        action_thresholds={
            "monitor": 0.15,
            "human_review": 0.25,
            "block": 0.60,
        }
    )

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

    # ── 协同传播注入逻辑 ─────────────────────────────────
    coordinated_done = False
    shared_narrative = None

    def coordinated_injection(step):
        nonlocal coordinated_done, shared_narrative

        if coordinated_done:
            return

        macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
        influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
        micro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MICRO]

        if step == 30 and macro_kols and shared_narrative is None:
            # 第一波：Macro KOL 创建叙事
            macro = macro_kols[0]
            shared_narrative = NarrativeEvent(
                name="龙头股将迎来重大利好，业绩将超预期",
                category=NarrativeCategory.EARNINGS,
                polarity=Polarity.POSITIVE,
                target_sector="tech",
                intensity=0.85,
                credibility=0.80,
                novelty=0.90,
                duration=80,
                source=macro.node_id,
            )
            narrative_engine.inject(shared_narrative)
            propagation.inject_narrative(shared_narrative)
            risk_agent.record_kol_spread(id(shared_narrative), macro.node_id)
            print(f"[Step {step}] [NARR] Macro KOL injected: {shared_narrative.name}")

        elif step == 32 and influencer_kols and shared_narrative:
            # 第二波：Influencer 接力（同一叙事）
            for inf in influencer_kols[:2]:
                risk_agent.record_kol_spread(id(shared_narrative), inf.node_id)
                print(f"[Step {step}] [COORDINATED] Influencer {inf.name} amplifying same narrative")

        elif step == 36 and micro_kols and shared_narrative:
            # 第三波：Micro 接力（跨层级协同）
            for mic in micro_kols[:3]:
                risk_agent.record_kol_spread(id(shared_narrative), mic.node_id)
                print(f"[Step {step}] [COORDINATED] Micro {mic.name} amplifying same narrative")
            coordinated_done = True

    # ── 主循环 ──────────────────────────────────────────
    print(f"\n{'Step':>6} | {'Price':>7} | {'Risk':>6} | {'Level':>10} | {'Patterns':>25}")
    print("-" * 80)

    risk_log = []
    coordinated_detected = False
    peak_risk = 0.0
    peak_risk_action = "allow"

    for step in range(steps):
        coordinated_injection(step)

        propagation.step()
        narrative_engine.tick()

        belief_updater.update_all(
            agents=agents, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine,
        )

        price_change = market.price_change_pct if market.price_history else 0.0
        narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)

        for agent in agents:
            action = agent.decide(market.get_snapshot(), emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)

        market.update_price(emotion)
        emotion.decay_toward_neutral(inertia=0.92)

        metrics = reflexivity_monitor.observe(
            step=step, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine, agents=agents,
        )

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
        if risk_report.manipulation_risk_score >= peak_risk:
            peak_risk = risk_report.manipulation_risk_score
            peak_risk_action = risk_report.recommended_action

        coordinated_detected = coordinated_detected or any(
            p.pattern.value == "coordinated_kol_amplification"
            for p in risk_report.detected_patterns
        )

        if step % 10 == 0 or risk_report.risk_level.value in ("high", "critical"):
            patterns = [p.pattern.value for p in risk_report.detected_patterns]
            print(
                f"{step:>6} | {market.price:>7.2f} | "
                f"{risk_report.manipulation_risk_score:>6.3f} | "
                f"{risk_report.risk_level.value:>10} | "
                f"{str(patterns[:3]):>25}"
            )

    # ── 结果摘要 ────────────────────────────────────────
    avg_risk = sum(risk_agent.risk_history) / len(risk_agent.risk_history)
    high_risk_steps = sum(1 for r in risk_agent.risk_history if r >= 0.50)

    result = {
        "demo": "coordinated_kol_amplification",
        "v0.4_risk_agent": True,
        "description": "Coordinated multi-KOL amplification -> HIGH manipulation risk",
        "steps": steps,
        "peak_manipulation_risk": round(peak_risk, 4),
        "avg_manipulation_risk": round(avg_risk, 4),
        "high_risk_steps": high_risk_steps,
        "coordinated_pattern_detected": coordinated_detected,
        "final_price": round(market.price, 2),
        "price_change_pct": round((market.price - 100.0) / 100.0, 4),
        "verification": {
            "peak_risk_gte_0.50": peak_risk >= 0.50,
            "coordinated_pattern_found": coordinated_detected,
            "required_action": peak_risk_action in ("human_review", "block"),
            "demo_sensitive_thresholds_used": risk_agent.action_thresholds != ManipulationRiskAgent.DEFAULT_ACTION_THRESHOLDS,
        }
    }

    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    print(f"  demo: {result['demo']}")
    print(f"  peak_manipulation_risk: {peak_risk:.4f} (target >= 0.50)")
    print(f"  coordinated_pattern_detected: {coordinated_detected}")
    print(f"  high_risk_steps: {high_risk_steps}")
    print("  demo_sensitive_thresholds_used: True")
    all_pass = all(result["verification"].values())
    print(f"\n  {'PASS' if all_pass else 'FAIL'}: "
          f"{'Coordinated amplification + HIGH risk' if all_pass else 'Test criteria not met'}")
    print(f"\n  Results saved to: {output_dir}/")
    return result


if __name__ == "__main__":
    run_demo_coordinated_kol_risk()
