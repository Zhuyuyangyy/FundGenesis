"""
experiments/demo_regulation_baseline.py
=========================================
Demo 10: Baseline — No Regulatory Intervention

V0.5 RegulatorAgent — 基线对照组（无干预）

实验设计：
  1. 模拟异常叙事传播场景（KOL协同 + 价格自证 + FOMO）
  2. ManipulationRiskAgent 持续输出高风险评分
  3. 但没有任何监管干预
  4. 200 steps 充分展示泡沫形成和崩塌

验收指标:
  - peak_manipulation_risk >= 0.50
  - high_risk_steps >= 20
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

from agents.emotional_retail import EmotionalRetailAgent
from agents.trend_follower import TrendFollowerAgent
from agents.value_investor import ValueInvestorAgent


def run_demo_baseline(output_dir: str = None, steps: int = 200):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.5_baseline"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 10: Baseline — No Regulatory Intervention")
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
    print(f"\n{'Step':>6} | {'Price':>7} | {'Risk':>6} | {'Level':>10} | {'Bubble':>6} | {'FOMO':>5}")
    print("-" * 70)

    risk_log = []
    metrics_log = []
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
        })
        metrics_log.append(metrics)

        if risk_score > peak_risk:
            peak_risk = risk_score
        if bubble_score > peak_bubble:
            peak_bubble = bubble_score
        if risk_score >= 0.25:
            high_risk_steps += 1
        if market.price > peak_price:
            peak_price = market.price

        if step % 15 == 0 or step in [25, 28, 33, 45, 55]:
            print(f"{step:>6} | {market.price:>7.2f} | {risk_score:>6.3f} | {risk_level:>10} | {bubble_score:>6.3f} | {risk_report.fomo_score:>5.3f}")

    final_price = market.price
    initial_price = market.price_history[0] if market.price_history else 100.0
    drawdown_from_peak = (final_price - peak_price) / peak_price * 100

    _plot_demo(risk_log, metrics_log, market.price_history, output_dir)

    result = {
        "demo": "baseline_no_intervention",
        "v0.5_regulator": True,
        "description": "No regulatory intervention - abnormal narrative propagates freely",
        "steps": steps,
        "peak_manipulation_risk": round(peak_risk, 4),
        "peak_bubble_risk": round(peak_bubble, 4),
        "high_risk_steps": high_risk_steps,
        "final_price": round(final_price, 2),
        "price_peak": round(peak_price, 2),
        "final_drawdown_pct": round(drawdown_from_peak, 2),
        "price_change_pct": round((final_price - initial_price) / initial_price * 100, 2),
        "verification": {
            "peak_risk_gte_0.50": peak_risk >= 0.50,
            "high_risk_steps_gte_20": high_risk_steps >= 20,
            "no_intervention_confirmed": True,
        }
    }

    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY — Demo 10 Baseline (No Intervention)")
    print("=" * 60)
    print(f"  peak_manipulation_risk: {peak_risk:.4f}")
    print(f"  peak_bubble_risk:      {peak_bubble:.4f}")
    print(f"  high_risk_steps:       {high_risk_steps}")
    print(f"  final_drawdown:        {drawdown_from_peak:.2f}%")
    print(f"\n  Results saved to: {output_dir}/")
    return result


def _plot_demo(risk_log, metrics_log, price_history, output_dir):
    price_slice = price_history[-len(risk_log):] if len(price_history) > len(risk_log) else price_history
    steps = range(len(risk_log))

    fig, axes = plt.subplots(3, 1, figsize=(13, 9))

    ax = axes[0]
    ax.plot(steps, price_slice, 'b-', linewidth=1.5, label="Price")
    ax.set_ylabel("Price")
    ax.set_title("Market Price (No Intervention)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    risk_scores = [r["risk_score"] for r in risk_log]
    bubble_scores = [r["bubble_score"] for r in risk_log]
    ax.plot(steps, risk_scores, 'r-', linewidth=1.5, label="Manipulation Risk")
    ax.plot(steps, bubble_scores, 'orange', linewidth=1.5, label="Bubble Risk")
    ax.set_ylabel("Risk Score")
    ax.set_title("Risk Scores")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    levels = [r["risk_level"] for r in risk_log]
    level_colors = {"low": "green", "medium": "yellow", "high": "orange", "critical": "red"}
    colors = [level_colors.get(l, "gray") for l in levels]
    ax.bar(list(steps), [1.0] * len(steps), color=colors, width=1.0)
    ax.set_ylabel("Risk Level")
    ax.set_xlabel("Step")
    ax.set_title("Risk Level Over Time")
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=l) for l, c in level_colors.items()]
    ax.legend(handles=legend_elements, loc="upper right")
    ax.set_yticks([])

    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "demo_baseline.png"), dpi=150)
    plt.close(fig)
    print(f"\n  Chart saved: {output_dir}/demo_baseline.png")


if __name__ == "__main__":
    run_demo_baseline()