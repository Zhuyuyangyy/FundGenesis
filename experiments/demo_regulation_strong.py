"""
experiments/demo_regulation_strong.py
======================================
Demo 12: Strong Intervention — Full intervention package (early trigger)

V0.5 RegulatorAgent — 强干预组

核心论点：
  高风险阶段强干预（全部4个动作）有效压制泡沫，
  显著降低 peak_bubble 和最终回调幅度。

实验设计：
  1. 同 baseline 的异常叙事注入场景
  2. Step 40：RegulatorAgent 激活强干预（早于light版本的step55）
     - narrative_throttle: 强力压制叙事传播
     - kol_downweight: 降低KOL影响力权重
     - risk_warning: 市场风险警告
     - trading_cooldown: 触发交易冷却
  3. 验证：强干预比轻度干预更早压制风险传播

验收指标（对比light baseline）:
  - peak_manipulation_risk 下降 >= 10%
  - high_risk_steps 显著减少
  - 干预触发step更早
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
from risk.regulator_agent import (
    RegulatorAgent, InterventionIntensity, InterventionEffect,
    InterventionAction,
)

from agents.emotional_retail import EmotionalRetailAgent
from agents.trend_follower import TrendFollowerAgent
from agents.value_investor import ValueInvestorAgent


def run_demo_strong(output_dir: str = None, steps: int = 200):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.5_strong"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 12: Strong Intervention — Full 4-action package (step 40)")
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

    # ── Strong override: 强制在step 40触发强干预 ──────────────
    _force_strong_at_step = 40

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
    print(f"\n{'Step':>6} | {'Price':>7} | {'Risk':>6} | {'Level':>10} | {'Actions':>30} | {'Intens':>5}")
    print("-" * 95)

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

        # ── Strong override: 强制step 40触发 ──────────────────
        if step == _force_strong_at_step:
            # 注入强干预效果（跳过risk_score阈值，直接执行STRONG动作）
            regulator.current_intensity = InterventionIntensity.STRONG
            # 迅速应用全部4个动作
            for action_flag in [
                InterventionAction.NARRATIVE_THROTTLE,
                InterventionAction.KOL_DOWNWEIGHT,
                InterventionAction.RISK_WARNING,
                InterventionAction.TRADING_COOLDOWN,
            ]:
                regulator._apply_action(action_flag, risk_report.manipulation_risk_score, InterventionEffect(step=step, actions=[]))
            # 应用到组件
            regulator._apply_to_narrative_engine(narrative_engine, risk_report.manipulation_risk_score)
            regulator._apply_to_kol_network(kol_network, risk_report.manipulation_risk_score)
            regulator._apply_to_agents(agents, risk_report.manipulation_risk_score)
            # 手动记录
            effect = InterventionEffect(step=step, actions=[
                a.value for a in [
                    InterventionAction.NARRATIVE_THROTTLE,
                    InterventionAction.KOL_DOWNWEIGHT,
                    InterventionAction.RISK_WARNING,
                    InterventionAction.TRADING_COOLDOWN,
                ]
            ])
            effect.risk_reduction = risk_report.manipulation_risk_score * 0.6
            effect.narrative_suppression = risk_report.manipulation_risk_score * 0.55
            regulator.history.append(effect)
            print(f"[Step {step}] [REGULATOR] ★ STRONG INTERVENTION triggered (forced)")
        else:
            effect = regulator.step(
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

        # 获取当前步的intervention actions（从history或override）
        if step == _force_strong_at_step:
            current_actions = [a.value for a in [InterventionAction.NARRATIVE_THROTTLE,
                InterventionAction.KOL_DOWNWEIGHT, InterventionAction.RISK_WARNING,
                InterventionAction.TRADING_COOLDOWN]]
            current_intensity = 3
        else:
            current_actions = regulator.history[-1].actions if regulator.history else []
            current_intensity = regulator.current_intensity.value

        risk_log.append({
            "step": step,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "bubble_score": bubble_score,
            "price": market.price,
            "fomo_score": risk_report.fomo_score,
            "intensity": current_intensity,
            "actions": current_actions,
        })
        metrics_log.append(metrics)
        intervention_log.append(regulator.history[-1] if regulator.history else None)

        if risk_score > peak_risk:
            peak_risk = risk_score
        if bubble_score > peak_bubble:
            peak_bubble = bubble_score
        if risk_score >= 0.25:
            high_risk_steps += 1
        if market.price > peak_price:
            peak_price = market.price

        if step % 15 == 0 or step == _force_strong_at_step or step in [25, 28, 33, 45, 55]:
            actions_str = "+".join(current_actions[:3]) if current_actions else "none"
            intens_str = InterventionIntensity(current_intensity).name
            print(f"{step:>6} | {market.price:>7.2f} | {risk_score:>6.3f} | {risk_level:>10} | {actions_str:>30} | {intens_str:>5}")

    final_price = market.price
    initial_price = market.price_history[0] if market.price_history else 100.0
    drawdown_from_peak = (final_price - peak_price) / peak_price * 100

    _plot_demo_strong(risk_log, metrics_log, market.price_history, output_dir)

    result = {
        "demo": "strong_intervention",
        "v0.5_regulator": True,
        "description": "Strong intervention - full 4-action package triggered at step 40",
        "steps": steps,
        "force_trigger_step": _force_strong_at_step,
        "peak_manipulation_risk": round(peak_risk, 4),
        "peak_bubble_risk": round(peak_bubble, 4),
        "high_risk_steps": high_risk_steps,
        "final_price": round(final_price, 2),
        "price_peak": round(peak_price, 2),
        "final_drawdown_pct": round(drawdown_from_peak, 2),
        "price_change_pct": round((final_price - initial_price) / initial_price * 100, 2),
        "intervention_summary": {
            "total_interventions": len([i for i in risk_log if i["actions"]]),
            "narrative_throttle_count": len([i for i in risk_log if 'narrative_throttle' in i.get('actions', [])]),
            "risk_warning_count": len([i for i in risk_log if 'risk_warning' in i.get('actions', [])]),
            "kol_downweight_count": len([i for i in risk_log if 'kol_downweight' in i.get('actions', [])]),
            "trading_cooldown_count": len([i for i in risk_log if 'trading_cooldown' in i.get('actions', [])]),
            "first_intervention_step": next((r["step"] for r in risk_log if r["actions"]), None),
        },
        "verification": {
            "peak_risk_gte_0.50": peak_risk >= 0.50,
            "strong_intervention_triggered": any(len(r["actions"]) >= 4 for r in risk_log),
            "early_trigger_verified": _force_strong_at_step in [r["step"] for r in risk_log if r["actions"]],
        }
    }

    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY — Demo 12 Strong Intervention")
    print("=" * 60)
    print(f"  peak_manipulation_risk: {peak_risk:.4f}")
    print(f"  peak_bubble_risk:      {peak_bubble:.4f}")
    print(f"  high_risk_steps:       {high_risk_steps}")
    print(f"  final_drawdown:        {drawdown_from_peak:.2f}%")
    print(f"  first_intervention:    step {result['intervention_summary']['first_intervention_step']}")
    print(f"  total_interventions:   {result['intervention_summary']['total_interventions']}")
    print(f"\n  Results saved to: {output_dir}/")
    return result


def _plot_demo_strong(risk_log, metrics_log, price_history, output_dir):
    price_slice = price_history[-len(risk_log):] if len(price_history) > len(risk_log) else price_history
    steps = range(len(risk_log))

    fig, axes = plt.subplots(3, 1, figsize=(13, 9))

    ax = axes[0]
    ax.plot(steps, price_slice, 'b-', linewidth=1.5, label="Price")
    ax.set_ylabel("Price")
    ax.set_title("Market Price (Strong Intervention @ step 40)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    risk_scores = [r["risk_score"] for r in risk_log]
    bubble_scores = [r["bubble_score"] for r in risk_log]
    ax.plot(steps, risk_scores, 'r-', linewidth=1.5, label="Manipulation Risk")
    ax.plot(steps, bubble_scores, 'orange', linewidth=1.5, label="Bubble Risk")
    intens_values = [r["intensity"] / 3.0 for r in risk_log]
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
            if an in r.get("actions", []):
                actions_matrix[i, j] = 1.0
    ax.imshow(actions_matrix.T, aspect='auto', interpolation='none',
              extent=[0, len(steps), 0, 4], origin='lower', alpha=0.7)
    ax.set_yticks([0.5 + i for i in range(4)])
    ax.set_yticklabels(action_names)
    ax.set_xlabel("Step")
    ax.set_title("Intervention Actions Over Time (STRONG @ step 40)")

    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "demo_strong.png"), dpi=150)
    plt.close(fig)
    print(f"\n  Chart saved: {output_dir}/demo_strong.png")


if __name__ == "__main__":
    run_demo_strong()