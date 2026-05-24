"""
experiments/demo_regulation_light.py
=====================================
Demo 11: Light Intervention — narrative_throttle + risk_warning

V0.5 RegulatorAgent — 轻度干预组

核心论点：
  早期干预（narrative_throttle + risk_warning）有效减缓叙事传播，
  降低峰值风险，缩短高风险持续时间。

实验设计：
  1. 同 baseline 的异常叙事注入场景
  2. Step 50：RegulatorAgent 激活轻度干预
     - narrative_throttle: 限制叙事传播速度
     - risk_warning: 向市场发出风险警告
  3. 验证：干预有效降低 peak_risk / high_risk_steps / peak_bubble

验收指标（对比baseline）:
  - peak_manipulation_risk 下降 >= 10%
  - high_risk_steps 减少 >= 20%
  - peak_bubble 下降 >= 15%
  - 干预动作：narrative_throttle + risk_warning
"""

import os, sys, json, numpy as np, matplotlib.pyplot as plt

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
from risk.manipulation_risk_agent import ManipulationRiskAgent, ManipulationRiskReport, RiskLevel
from risk.regulator_agent import RegulatorAgent, InterventionIntensity, InterventionEffect

from agents.emotional_retail import EmotionalRetailAgent
from agents.trend_follower import TrendFollowerAgent
from agents.value_investor import ValueInvestorAgent


def run_demo_light(output_dir: str = None, steps: int = 200):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.5_light"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 11: Light Intervention — narrative_throttle + risk_warning")
    print("=" * 60)

    controller = CreatorController(
        market_config=MarketConfig(
            initial_price=100.0,
            impact_coefficient=0.20,
            noise_std=0.008,
            total_agents=100,
        ),
        emotion_config={
            "initial_fear": 0.15,
            "initial_greed": 0.60,
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
    risk_agent = ManipulationRiskAgent(action_thresholds={
        "monitor": 0.15,
        "human_review": 0.25,
        "block": 0.60,
    })
    regulator = RegulatorAgent()

    agents = []
    for i in range(100):
        if i < 10:
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        elif i < 40:
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        else:
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

    macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
    influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
    micro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MICRO]

    shared_narrative = None
    injection_done = {}

    def inject_abnormal_narrative(step):
        nonlocal shared_narrative, injection_done
        if step in injection_done:
            return
        injection_done[step] = True

        if step == 25 and macro_kols:
            shared_narrative = NarrativeEvent(
                name="龙头股业绩将超预期，AI革命将改变一切",
                category=NarrativeCategory.EARNINGS,
                polarity=Polarity.POSITIVE,
                target_sector="tech",
                intensity=0.88,
                credibility=0.82,
                novelty=0.90,
                duration=80,
                source=macro_kols[0].node_id,
            )
            narrative_engine.inject(shared_narrative)
            propagation.inject_narrative(shared_narrative)
            risk_agent.record_kol_spread(shared_narrative._id, macro_kols[0].node_id)
            print(f"[Step {step}] [WAVE1] Macro KOL injected narrative")

        elif step == 28 and influencer_kols and shared_narrative:
            for inf in influencer_kols[:3]:
                risk_agent.record_kol_spread(shared_narrative._id, inf.node_id)
            print(f"[Step {step}] [WAVE2] Influencers amplifying")

        elif step == 33 and micro_kols and shared_narrative:
            for mic in micro_kols[:4]:
                risk_agent.record_kol_spread(shared_narrative._id, mic.node_id)
            print(f"[Step {step}] [WAVE3] Micro KOLs cross-tier amplification")

        elif step == 45 and shared_narrative:
            risk_agent.record_price_feedback(
                narrative_id=shared_narrative._id,
                price_change=0.03,
                confirmation_strength=0.72,
                step=step
            )
            print(f"[Step {step}] [PRICE_VALIDATION] Price self-validation event injected")

        elif step == 55:
            risk_agent.record_fomo_signal(
                retail_buy_ratio=0.78,
                greed_level=0.82,
                belief_concentration=0.70,
                step=step
            )
            print(f"[Step {step}] [FOMO] Retail FOMO surge signal injected")

    # ── 主循环 ──────────────────────────────────────────
    print(f"\n{'Step':>6} | {'Price':>7} | {'Risk':>6} | {'Level':>10} | {'Actions':>25} | {'Intens':>5}")
    print("-" * 90)

    risk_log = []
    metrics_log = []
    intervention_log = []
    peak_risk = 0.0
    peak_bubble = 0.0
    high_risk_steps = 0
    peak_price = 0.0

    for step in range(steps):
        inject_abnormal_narrative(step)
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
        emotion.decay_toward_neutral(inertia=0.90)

        metrics = reflexivity_monitor.observe(
            step=step, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine, agents=agents,
        )

        risk_report = risk_agent.evaluate(
            step=step, kol_network=kol_network, trust_engine=trust_engine,
            reflexivity_monitor=reflexivity_monitor, market=market,
            narrative_engine=narrative_engine, propagation_model=propagation,
            agents=agents,
        )

        # RegulatorAgent 干预决策
        manipulation_flags = {
            "coordinated_detected": any(p.pattern == "coordinated_kol_amplification" for p in risk_report.detected_patterns),
            "fomo_detected": risk_report.fomo_score > 0.3,
            "self_validation_detected": risk_report.self_validation_score > 0.3,
        }
        market_state = {
            "price": market.price,
            "bubble_risk": metrics.bubble_risk_score,
            "retail_fomo": risk_report.fomo_score,
            "price_volatility": metrics.volatility,
        }
        intervention = regulator.step(
            risk_score=risk_report.manipulation_risk_score,
            market_state=market_state,
            manipulation_flags=manipulation_flags,
            narrative_engine=narrative_engine,
            kol_network=kol_network,
            agents=agents,
        )

        risk_score = risk_report.manipulation_risk_score
        bubble_score = metrics.bubble_risk_score
        risk_level = risk_report.risk_level.value if hasattr(risk_report.risk_level, 'value') else risk_report.risk_level

        risk_log.append({
            "step": step,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "bubble_score": bubble_score,
            "price": market.price,
            "fomo_score": risk_report.fomo_score,
            "intensity": regulator.current_intensity.value,
            "actions": intervention.actions,
        })
        metrics_log.append(metrics)
        intervention_log.append(intervention)

        if risk_score > peak_risk:
            peak_risk = risk_score
        if bubble_score > peak_bubble:
            peak_bubble = bubble_score
        if risk_score >= 0.25:
            high_risk_steps += 1
        if market.price > peak_price:
            peak_price = market.price

        if step % 15 == 0 or step in [25, 28, 33, 45, 55]:
            actions_str = "+".join(intervention.actions[:2]) if intervention.actions else "none"
            intens_str = regulator.current_intensity.name
            print(f"{step:>6} | {market.price:>7.2f} | {risk_score:>6.3f} | {risk_level:>10} | {actions_str:>25} | {intens_str:>5}")

    final_price = market.price
    initial_price = market.price_history[0] if market.price_history else 100.0
    drawdown_from_peak = (final_price - peak_price) / peak_price * 100

    _plot_demo_light(risk_log, metrics_log, market.price_history, output_dir)

    result = {
        "demo": "light_intervention",
        "v0.5_regulator": True,
        "description": "Light intervention - narrative_throttle + risk_warning",
        "steps": steps,
        "peak_manipulation_risk": round(peak_risk, 4),
        "peak_bubble_risk": round(peak_bubble, 4),
        "high_risk_steps": high_risk_steps,
        "final_price": round(final_price, 2),
        "price_peak": round(peak_price, 2),
        "final_drawdown_pct": round(drawdown_from_peak, 2),
        "price_change_pct": round((final_price - initial_price) / initial_price * 100, 2),
        "intervention_summary": {
            "total_interventions": len([i for i in intervention_log if i.actions]),
            "narrative_throttle_count": len([i for i in intervention_log if 'narrative_throttle' in i.actions]),
            "risk_warning_count": len([i for i in intervention_log if 'risk_warning' in i.actions]),
            "kol_downweight_count": len([i for i in intervention_log if 'kol_downweight' in i.actions]),
            "trading_cooldown_count": len([i for i in intervention_log if 'trading_cooldown' in i.actions]),
        },
        "verification": {
            "peak_risk_gte_0.50": peak_risk >= 0.50,
            "high_risk_steps_gte_20": high_risk_steps >= 20,
            "intervention_triggered": len([i for i in intervention_log if i.actions]) > 0,
        }
    }

    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY — Demo 11 Light Intervention")
    print("=" * 60)
    print(f"  peak_manipulation_risk: {peak_risk:.4f}")
    print(f"  peak_bubble_risk:      {peak_bubble:.4f}")
    print(f"  high_risk_steps:       {high_risk_steps}")
    print(f"  final_drawdown:        {drawdown_from_peak:.2f}%")
    print(f"  total_interventions:   {result['intervention_summary']['total_interventions']}")
    print(f"\n  Results saved to: {output_dir}/")
    return result


def _plot_demo_light(risk_log, metrics_log, price_history, output_dir):
    price_slice = price_history[-len(risk_log):] if len(price_history) > len(risk_log) else price_history
    steps = range(len(risk_log))

    fig, axes = plt.subplots(3, 1, figsize=(13, 9))

    ax = axes[0]
    ax.plot(steps, price_slice, 'b-', linewidth=1.5, label="Price")
    ax.set_ylabel("Price")
    ax.set_title("Market Price (Light Intervention)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    risk_scores = [r["risk_score"] for r in risk_log]
    bubble_scores = [r["bubble_score"] for r in risk_log]
    ax.plot(steps, risk_scores, 'r-', linewidth=1.5, label="Manipulation Risk")
    ax.plot(steps, bubble_scores, 'orange', linewidth=1.5, label="Bubble Risk")
    intens_values = [r["intensity"] / 3.0 for r in risk_log]  # normalize to [0,1]
    ax2 = ax.twinx()
    ax2.fill_between(steps, intens_values, alpha=0.2, color='blue', label="Intervention Intensity")
    ax.set_ylabel("Risk Score")
    ax.set_title("Risk Scores + Intervention Intensity")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    actions_matrix = np.zeros((len(steps), 4))
    action_names = ['narrative_throttle', 'risk_warning', 'kol_downweight', 'trading_cooldown']
    for i, r in enumerate(risk_log):
        for j, an in enumerate(action_names):
            if an in r["actions"]:
                actions_matrix[i, j] = 1.0
    ax.imshow(actions_matrix.T, aspect='auto', interpolation='none',
              extent=[0, len(steps), 0, 4], origin='lower', alpha=0.7)
    ax.set_yticks([0.5 + i for i in range(4)])
    ax.set_yticklabels(action_names)
    ax.set_xlabel("Step")
    ax.set_title("Intervention Actions Over Time")

    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "demo_light.png"), dpi=150)
    plt.close(fig)
    print(f"\n  Chart saved: {output_dir}/demo_light.png")


if __name__ == "__main__":
    run_demo_light()