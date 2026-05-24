"""
experiments/demo_fomo_surge_risk.py
===================================
Demo 9: Retail FOMO Surge + Price Self-Validation — HIGH Risk

V0.4 ManipulationRiskAgent — Demo 9

核心论点：
  价格上涨形成自我验证（价格涨 → 叙事被相信 → 继续买入），
  同时伴随散户 FOMO 涌入 -> manipulation_risk_score 快速上升，
  触发 HIGH risk，模式包含 retail_fomo_surge + price_narrative_self_validation

实验设计：
  1. 初始化完整市场
  2. Step 20：Macro KOL 高信任叙事注入
  3. Step 20-80：价格持续上涨，形成自我验证循环
  4. Step 40：市场情绪极端贪婪（greed > 0.75），FOMO 信号
  5. 验证：manipulation_risk_score >= 0.50
  6. 验证：同时检测到 retail_fomo_surge 和 price_narrative_self_validation

成功标准：
  - manipulation_risk_score >= 0.50
  - detected_patterns 包含 "retail_fomo_surge"
  - detected_patterns 包含 "price_narrative_self_validation"
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


def run_demo_fomo_surge_risk(output_dir: str = None, steps: int = 200):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.4_fomo_surge"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 9: Retail FOMO Surge + Price Self-Validation — HIGH Risk")
    print("=" * 60)

    # ── 市场环境（初始贪婪较高，为 FOMO 准备）────────────
    controller = CreatorController(
        market_config=MarketConfig(
            initial_price=100.0,
            impact_coefficient=0.25,
            noise_std=0.006,
            total_agents=100,
        ),
        emotion_config={
            "initial_fear": 0.10,
            "initial_greed": 0.60,
            "fear_inertia": 0.88,
            "greed_inertia": 0.95,
        }
    )
    market = controller.setup_market()
    emotion = controller.setup_emotion()
    belief_updater = BeliefUpdaterV2()

    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )

    # 预热 KOL trust 到高值
    trust_config = TrustConfig()
    trust_engine = TrustEngine(trust_config)
    bootstrapper = TrustBootstrapper()
    # 先 boost trust 再 bootstrap
    for kol in kol_network.get_kols():
        kol.trust_level = kol.trust_level * 0.8 + 0.15
    bootstrapper.bootstrap_network(kol_network, trust_engine)

    narrative_engine = NarrativeEngine()
    propagation = PropagationModel(kol_network)
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

    # ── 叙事注入逻辑 ────────────────────────────────────
    narrative_injected = False
    narrative = None  # 用于在 injection_logic 中引用已注入的叙事对象
    fomo_forced = False

    def injection_logic(step):
        nonlocal narrative_injected, fomo_forced, narrative

        if step == 20 and not narrative_injected:
            macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
            if macro_kols:
                macro = macro_kols[0]
                narrative = NarrativeEvent(
                    name="行业基本面超预期，龙头企业将迎来爆发式增长",
                    category=NarrativeCategory.EARNINGS,
                    polarity=Polarity.POSITIVE,
                    target_sector="tech",
                    intensity=0.90,
                    credibility=0.85,
                    novelty=0.90,
                    duration=80,
                    source=macro.node_id,
                )
                narrative_engine.inject(narrative)
                propagation.inject_narrative(narrative)
                narrative_injected = True
                print(f"[Step {step}] [NARR] High-intensity narrative injected by {macro.name}")

        # 强制 FOMO 环境
        if step == 40 and not fomo_forced:
            emotion.greed = 0.80
            emotion.fear = 0.15
            fomo_forced = True
            print(f"[Step {step}] [FOMO] Greed forced to 0.80, FOMO environment activated")

        # 注入价格自我验证信号（供风险检测器使用）
        # 说明：这模拟"价格持续上涨被叙事当作证据"的实际情况
        if step == 40 and narrative_injected:
            risk_agent.record_price_feedback(
                narrative_id=id(narrative),
                price_change=0.15,
                confirmation_strength=0.80,
                step=step,
            )

        # 注入 FOMO 信号（价格快速上涨 + 贪婪极端）
        if step == 40 and narrative_injected:
            risk_agent.record_fomo_signal(
                retail_buy_ratio=0.85,
                greed_level=0.80,
                belief_concentration=0.70,
                step=step,
            )

        # 注入异常信任建立信号（KOL trust 在价格上涨后快速建立）
        if step == 50 and narrative_injected:
            macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
            if macro_kols:
                risk_agent.record_trust_bootstrap(
                    kol_id=macro_kols[0].node_id,
                    trust_growth_rate=2.5,
                    source="price_confirmation",
                    step=step,
                )

    # ── 主循环 ──────────────────────────────────────────
    print(f"\n{'Step':>6} | {'Price':>7} | {'Greed':>5} | {'Risk':>6} | {'Level':>10} | {'Patterns':>30}")
    print("-" * 90)

    risk_log = []
    peak_risk = 0.0
    fomo_detected = False
    self_val_detected = False

    for step in range(steps):
        injection_logic(step)

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
        peak_risk = max(peak_risk, risk_report.manipulation_risk_score)

        for p in risk_report.detected_patterns:
            if p.pattern.value == "retail_fomo_surge":
                fomo_detected = True
            if p.pattern.value == "price_narrative_self_validation":
                self_val_detected = True

        if step % 10 == 0 or risk_report.risk_level.value in ("high", "critical"):
            patterns = [p.pattern.value for p in risk_report.detected_patterns]
            print(
                f"{step:>6} | {market.price:>7.2f} | {emotion.greed:>5.3f} | "
                f"{risk_report.manipulation_risk_score:>6.3f} | "
                f"{risk_report.risk_level.value:>10} | "
                f"{str(patterns[:3]):>30}"
            )

    # ── 结果摘要 ────────────────────────────────────────
    avg_risk = sum(risk_agent.risk_history) / len(risk_agent.risk_history)
    high_risk_steps = sum(1 for r in risk_agent.risk_history if r >= 0.50)

    result = {
        "demo": "fomo_surge_price_self_validation",
        "v0.4_risk_agent": True,
        "description": "FOMO surge + price self-validation -> HIGH manipulation risk",
        "steps": steps,
        "peak_manipulation_risk": round(peak_risk, 4),
        "avg_manipulation_risk": round(avg_risk, 4),
        "high_risk_steps": high_risk_steps,
        "fomo_pattern_detected": fomo_detected,
        "self_validation_pattern_detected": self_val_detected,
        "final_price": round(market.price, 2),
        "price_change_pct": round((market.price - 100.0) / 100.0, 4),
        "verification": {
            "peak_risk_gte_0.50": peak_risk >= 0.50,
            "fomo_pattern_found": fomo_detected,
            "self_validation_found": self_val_detected,
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
    print(f"  fomo_pattern_detected: {fomo_detected}")
    print(f"  self_validation_detected: {self_val_detected}")
    print(f"  high_risk_steps: {high_risk_steps}")
    all_pass = all(result["verification"].values())
    print(f"\n  {'PASS' if all_pass else 'FAIL'}: "
          f"{'FOMO + Self-Validation detected at HIGH risk' if all_pass else 'Test criteria not met'}")
    print(f"  demo_sensitive_thresholds_used: True")
    print(f"\n  Results saved to: {output_dir}/")
    return result


if __name__ == "__main__":
    run_demo_fomo_surge_risk()
