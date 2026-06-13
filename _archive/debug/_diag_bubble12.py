"""
Deep diagnostic: trace narrative_strength, belief_concentration, and bubble_risk
at key steps for all three scenarios. Use exact demo loop logic.
"""
import sys, os, numpy as np
sys.path.insert(0, '.')

from core.creator_controller import CreatorController, MarketConfig
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor
from risk.manipulation_risk_agent import ManipulationRiskAgent
from risk.regulator_agent import RegulatorAgent, InterventionIntensity, InterventionAction, InterventionEffect
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from agents.value_investor import ValueInvestorAgent
from agents.trend_follower import TrendFollowerAgent
from agents.emotional_retail import EmotionalRetailAgent

def build_env():
    c = CreatorController(MarketConfig(initial_price=100.0, impact_coefficient=0.20, noise_std=0.008, total_agents=100),
                          {'initial_fear': 0.15, 'initial_greed': 0.60, 'fear_inertia': 0.92, 'greed_inertia': 0.92})
    market = c.setup_market()
    emotion = c.setup_emotion()
    belief_updater = BeliefUpdaterV2()
    kol_network = KOLNetwork().build_default_network(n_macro=2, n_influencer=5, n_micro=10, n_retail=100)
    narrative_engine = NarrativeEngine()
    propagation = PropagationModel(kol_network)
    trust_config = TrustConfig()
    trust_engine = TrustEngine(trust_config)
    bootstrapper = TrustBootstrapper()
    bootstrapper.bootstrap_network(kol_network, trust_engine)
    reflexivity_monitor = ReflexivityMonitor()
    risk_agent = ManipulationRiskAgent(action_thresholds={"monitor": 0.15, "human_review": 0.25, "block": 0.60})
    regulator = RegulatorAgent()
    agents = []
    for i in range(100):
        if i < 10: agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        elif i < 40: agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        else: agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))
    macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
    influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
    micro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MICRO]
    return (market, emotion, belief_updater, kol_network, narrative_engine, propagation,
            trust_engine, reflexivity_monitor, risk_agent, regulator, agents,
            macro_kols, influencer_kols, micro_kols)

def run_scenario(name, intervention_step, intensity_override):
    (market, emotion, belief_updater, kol_network, narrative_engine, propagation,
     trust_engine, reflexivity_monitor, risk_agent, regulator, agents,
     macro_kols, influencer_kols, micro_kols) = build_env()

    shared_narrative = [None]
    peak_bubble = 0.0

    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"{'='*80}")

    for step in range(200):
        # --- Narrative injection (same for all 3 scenarios) ---
        if step == 25 and macro_kols:
            shared_narrative[0] = NarrativeEvent(name="龙头股业绩将超预期",
                category=NarrativeCategory.EARNINGS, polarity=Polarity.POSITIVE, target_sector="tech",
                intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
                source=macro_kols[0].node_id)
            narrative_engine.inject(shared_narrative[0])
            propagation.inject_narrative(shared_narrative[0])
            risk_agent.record_kol_spread(shared_narrative[0]._id, macro_kols[0].node_id)
        elif step == 28 and influencer_kols and shared_narrative[0]:
            for inf in influencer_kols[:3]:
                risk_agent.record_kol_spread(shared_narrative[0]._id, inf.node_id)
        elif step == 33 and micro_kols and shared_narrative[0]:
            for mic in micro_kols[:4]:
                risk_agent.record_kol_spread(shared_narrative[0]._id, mic.node_id)
        elif step == 45 and shared_narrative[0]:
            risk_agent.record_price_feedback(shared_narrative[0]._id, 0.03, 0.72, step)
        elif step == 55:
            risk_agent.record_fomo_signal(0.78, 0.82, 0.70, step)

        # --- Standard demo loop ---
        propagation.step()
        narrative_engine.tick()
        belief_updater.update_all(agents=agents, market=market, emotion=emotion,
                                  kol_network=kol_network, narrative_engine=narrative_engine)
        price_change = market.price_change_pct if market.price_history else 0.0
        narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)

        for agent in agents:
            action = agent.decide(market.get_snapshot(), emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)

        market.update_price(emotion)
        emotion.decay_toward_neutral(inertia=0.90)

        metrics = reflexivity_monitor.observe(step=step, market=market, emotion=emotion,
                                              kol_network=kol_network, narrative_engine=narrative_engine, agents=agents)
        risk_report = risk_agent.evaluate(step=step, kol_network=kol_network, trust_engine=trust_engine,
                                          reflexivity_monitor=reflexivity_monitor, market=market,
                                          narrative_engine=narrative_engine, propagation_model=propagation, agents=agents)

        peak_bubble = max(peak_bubble, metrics.bubble_risk_score)

        # --- Intervention (only if specified) ---
        if intervention_step is not None and step == intervention_step:
            if intensity_override is not None:
                regulator.current_intensity = intensity_override
            action_set = regulator._get_action_set(regulator.current_intensity)
            effect = InterventionEffect(step=step, actions=action_set)
            for action in action_set:
                regulator._apply_action(risk_report.manipulation_risk_score, effect)
            regulator._apply_to_narrative_engine(narrative_engine, risk_report.manipulation_risk_score)
            print(f"  [Step {step}] ★ {intensity_override.name if intensity_override else 'INTERVENTION'} → "
                  f"narrative_cap={regulator.state.narrative_cap:.3f} "
                  f"multiplier={narrative_engine.narrative_strength_multiplier:.3f} "
                  f"actions={[a.value for a in action_set]}")

        # Print at key steps
        if step in [25, 28, 33, 40, 45, 50, 55, 60, 65, 70, 80, 90]:
            ns_eff = narrative_engine.narrative_strength()
            stats = kol_network.belief_statistics()
            bc = stats['belief_concentration']
            print(f"  Step {step:>3}: price={market.price:>7.2f} bubble={metrics.bubble_risk_score:.4f} "
                  f"manip={risk_report.manipulation_risk_score:.3f} "
                  f"bc={bc:.4f} ns_eff={ns_eff:.4f} "
                  f"ea={metrics.emotion_amplification:.4f} vol={metrics.volatility:.5f} "
                  f"cf={metrics.capital_imbalance:.4f} mult={narrative_engine.narrative_strength_multiplier:.3f}")

    print(f"\n  PEAK bubble_risk: {peak_bubble:.4f}")
    return peak_bubble

# Run all three
b = run_scenario("BASELINE (no intervention)", intervention_step=None, intensity_override=None)
l = run_scenario("LIGHT (intervention at step 55)", intervention_step=55, intensity_override=InterventionIntensity.LIGHT)
s = run_scenario("STRONG (intervention at step 40)", intervention_step=40, intensity_override=InterventionIntensity.STRONG)

print(f"\n{'='*60}")
print("FINAL COMPARISON")
print(f"{'='*60}")
print(f"  Baseline: {b:.4f}")
print(f"  Light:    {l:.4f}")
print(f"  Strong:   {s:.4f}")
if s < l < b:
    print("  ✅ PASS: Strong < Light < Baseline")
elif s > l > b:
    print("  ⚠️  INVERTED: Strong > Light > Baseline (but expected for peak_bubble when Strong peaks early)")
else:
    print(f"  ❓ UNCLEAR ORDERING")