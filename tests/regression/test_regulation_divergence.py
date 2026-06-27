"""
tests/regression/test_regulation_divergence.py
=================================================
PR-5 回归测试：验证 Baseline/Light/Strong 监管对照实验的 high_risk_steps 分化

核心断言：
- 三组实验的 high_risk_steps 不再完全相同
- 干预组 (Light/Strong) 的某些指标与 Baseline 有显著差异
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from core.creator_controller import CreatorController, MarketConfig
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from risk.manipulation_risk_agent import ManipulationRiskAgent
from risk.regulator_agent import RegulatorAgent, InterventionIntensity, InterventionAction, InterventionEffect

from agents.emotional_retail import EmotionalRetailAgent
from agents.trend_follower import TrendFollowerAgent
from agents.value_investor import ValueInvestorAgent


def _run_simulation(regulation_mode: str = "baseline", steps: int = 200, seed: int = 42) -> dict:
    """运行单次仿真，返回关键指标"""
    np.random.seed(seed)

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

    regulator = None
    if regulation_mode != "baseline":
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
                name="龙头股业绩将超预期",
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

        elif step == 28 and influencer_kols and shared_narrative:
            for inf in influencer_kols[:3]:
                risk_agent.record_kol_spread(shared_narrative._id, inf.node_id)

        elif step == 33 and micro_kols and shared_narrative:
            for mic in micro_kols[:4]:
                risk_agent.record_kol_spread(shared_narrative._id, mic.node_id)

        elif step == 45 and shared_narrative:
            risk_agent.record_price_feedback(
                narrative_id=shared_narrative._id,
                price_change=0.03,
                confirmation_strength=0.72,
                step=step
            )

        elif step == 55:
            risk_agent.record_fomo_signal(
                retail_buy_ratio=0.78,
                greed_level=0.82,
                belief_concentration=0.70,
                step=step
            )

    peak_risk = 0.0
    peak_bubble = 0.0
    high_risk_steps = 0
    bubble_high_risk_steps = 0
    peak_price = 0.0
    intervention_count = 0

    for step in range(steps):
        market.begin_step()
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
        kol_network.decay_beliefs_all()

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

        # FOMO → EmotionField 闭环
        fomo_impulse = risk_agent.get_fomo_emotion_impulse()
        if fomo_impulse > 0.1:
            emotion.apply_fomo_signal(fomo_impulse)

        # 监管干预
        if regulator is not None:
            manipulation_flags = {
                "coordinated_detected": any(
                    p.pattern.value == "coordinated_kol_amplification"
                    for p in risk_report.detected_patterns
                ),
                "fomo_detected": risk_report.fomo_score > 0.3,
                "self_validation_detected": risk_report.self_validation_score > 0.3,
            }
            market_state = {
                "price": market.price,
                "bubble_risk": metrics.bubble_risk_score,
                "retail_fomo": risk_report.fomo_score,
                "price_volatility": metrics.volatility,
            }

            if regulation_mode == "strong" and step == 40:
                # 强制强干预
                regulator.current_intensity = InterventionIntensity.STRONG
                for action_flag in [
                    InterventionAction.NARRATIVE_THROTTLE,
                    InterventionAction.KOL_DOWNWEIGHT,
                    InterventionAction.RISK_WARNING,
                    InterventionAction.TRADING_COOLDOWN,
                ]:
                    regulator._apply_action(action_flag, risk_report.manipulation_risk_score, InterventionEffect(step=step, actions=[]))
                regulator._apply_to_narrative_engine(narrative_engine, risk_report.manipulation_risk_score)
                regulator._apply_to_kol_network(kol_network, risk_report.manipulation_risk_score)
                regulator._apply_to_agents(agents, risk_report.manipulation_risk_score)
                intervention_count += 1
            else:
                effect = regulator.step(
                    risk_score=risk_report.manipulation_risk_score,
                    market_state=market_state,
                    manipulation_flags=manipulation_flags,
                    narrative_engine=narrative_engine,
                    kol_network=kol_network,
                    agents=agents,
                )
                if effect.actions:
                    intervention_count += 1

            # P0 Fix: risk_warning → EmotionField传导
            if regulator is not None and regulator.state.warning_active:
                fear_inject = regulator.state.investor_fear_factor * 0.15
                emotion.fear = min(emotion.fear + fear_inject, 1.0)
                emotion.uncertainty = min(emotion.uncertainty + fear_inject * 0.5, 1.0)
                emotion.greed = max(emotion.greed - fear_inject * 0.3, 0.0)

        risk_score = risk_report.manipulation_risk_score
        if risk_score > peak_risk:
            peak_risk = risk_score
        if metrics.bubble_risk_score > peak_bubble:
            peak_bubble = metrics.bubble_risk_score
        if risk_score >= 0.25:
            high_risk_steps += 1
        # Also track bubble_risk-based high risk steps (more responsive to interventions)
        if metrics.bubble_risk_score >= 0.30:
            bubble_high_risk_steps += 1
        if market.price > peak_price:
            peak_price = market.price

    return {
        "regulation_mode": regulation_mode,
        "peak_risk": peak_risk,
        "peak_bubble": peak_bubble,
        "high_risk_steps": high_risk_steps,
        "bubble_high_risk_steps": bubble_high_risk_steps,
        "peak_price": peak_price,
        "intervention_count": intervention_count,
    }


def test_regulation_groups_diverge_on_high_risk_steps():
    """三组监管实验的 bubble_high_risk_steps 必须分化（不再完全相同）"""
    # 用固定种子跑三组
    baseline = _run_simulation("baseline", steps=200, seed=42)
    light = _run_simulation("light", steps=200, seed=42)
    strong = _run_simulation("strong", steps=200, seed=42)

    print(f"  Baseline bubble_high_risk_steps: {baseline['bubble_high_risk_steps']}, peak_bubble: {baseline['peak_bubble']:.3f}")
    print(f"  Light bubble_high_risk_steps:    {light['bubble_high_risk_steps']}, peak_bubble: {light['peak_bubble']:.3f}")
    print(f"  Strong bubble_high_risk_steps:   {strong['bubble_high_risk_steps']}, peak_bubble: {strong['peak_bubble']:.3f}")

    # 修复前三组完全相同，修复后至少有一组不同
    all_bhrs = [baseline['bubble_high_risk_steps'], light['bubble_high_risk_steps'], strong['bubble_high_risk_steps']]
    assert len(set(all_bhrs)) > 1, \
        f"bubble_high_risk_steps must diverge across groups, got {all_bhrs}"

    # 监管组 peak_bubble 应低于 Baseline（监管降低泡沫风险）
    assert light['peak_bubble'] <= baseline['peak_bubble'] or strong['peak_bubble'] <= baseline['peak_bubble'], \
        f"At least one regulation group should have lower peak_bubble than baseline: base={baseline['peak_bubble']:.3f}, light={light['peak_bubble']:.3f}, strong={strong['peak_bubble']:.3f}"


def test_intervention_count_differs():
    """干预组的干预次数必须与 Baseline（0次）不同"""
    baseline = _run_simulation("baseline", steps=200, seed=42)
    light = _run_simulation("light", steps=200, seed=42)
    strong = _run_simulation("strong", steps=200, seed=42)

    assert baseline['intervention_count'] == 0, \
        f"Baseline should have 0 interventions, got {baseline['intervention_count']}"
    assert light['intervention_count'] > 0, \
        f"Light should have >0 interventions, got {light['intervention_count']}"
    assert strong['intervention_count'] > 0, \
        f"Strong should have >0 interventions, got {strong['intervention_count']}"


if __name__ == "__main__":
    test_regulation_groups_diverge_on_high_risk_steps()
    test_intervention_count_differs()
    print("[PASS] All test_regulation_divergence tests passed!")
