"""
Full diagnostic: trace bubble_risk through demo loop with intervention tracking.
Compare Baseline vs Light vs Strong to see if ordering works.
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
from risk.regulator_agent import RegulatorAgent, InterventionEffect
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

def inject_scene(step, kol_network, narrative_engine, propagation, risk_agent,
                 macro_kols, influencer_kols, micro_kols, shared_narrative):
    injected = {}
    if step == 25 and macro_kols:
        shared_narrative[0] = NarrativeEvent(name="龙头股业绩将超预期", category=NarrativeCategory.EARNINGS,
            polarity=Polarity.POSITIVE, target_sector="tech", intensity=0.88, credibility=0.82,
            novelty=0.90, duration=80, source=macro_kols[0].node_id)
        narrative_engine.inject(shared_narrative[0])
        propagation.inject_narrative(shared_narrative[0])
        risk_agent.record_kol_spread(shared_narrative[0]._id, macro_kols[0].node_id)
        injected['wave1'] = True
    elif step == 28 and influencer_kols and shared_narrative[0]:
        for inf in influencer_kols[:3]:
            risk_agent.record_kol_spread(shared_narrative[0]._id, inf.node_id)
        injected['wave2'] = True
    elif step == 33 and micro_kols and shared_narrative[0]:
        for mic in micro_kols[:4]:
            risk_agent.record_kol_spread(shared_narrative[0]._id, mic.node_id)
        injected['wave3'] = True
    elif step == 45 and shared_narrative[0]:
        risk_agent.record_price_feedback(shared_narrative[0]._id, 0.03, 0.72, step)
        injected['price_val'] = True
    elif step == 55:
        risk_agent.record_fomo_signal(0.78, 0.82, 0.70, step)
        injected['fomo'] = True
    return injected

def run_scenario(scenario_name, intervention_step, intervention_intensity_override=None):
    (market, emotion, belief_updater, kol_network, narrative_engine, propagation,
     trust_engine, reflexivity_monitor, risk_agent, regulator, agents,
     macro_kols, influencer_kols, micro_kols) = build_env()

    shared_narrative = [None]
    injection_log = {}
    peak_bubble = 0.0
    peak_manip = 0.0
    high_risk_steps = 0

    print(f"\n{'='*70}")
    print(f"Scenario: {scenario_name}")
    print(f"{'='*70}")
    print(f"{'Step':>4} | {'Price':>7} | {'Risk':>6} | {'Bubble':>6} | {'ns_raw':>6} | {'ns_eff':>6} | {'multiplier':>9} | {'narr_cap':>8} | {'Actions'}")
    print(f"{'-'*100}")

    for step in range(200):
        injected = inject_scene(step, kol_network, narrative_engine, propagation, risk_agent,
                                macro_kols, influencer_kols, micro_kols, shared_narrative)
        if injected: print(f"[Step {step}] Injected: {', '.join(injected.keys())}")

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
        risk_score = risk_report.manipulation_risk_score
        bubble_score = metrics.bubble_risk_score
        peak_bubble = max(peak_bubble, bubble_score)
        peak_manip = max(peak_manip, risk_score)
        if risk_score >= 0.25: high_risk_steps += 1

        # Intervention logic
        actions_taken = []
        ns_raw = sum(e.effective_intensity * e.credibility for e in narrative_engine.registry.active)
        ns_eff = narrative_engine.narrative_strength()
        multiplier = narrative_engine.narrative_strength_multiplier

        if intervention_intensity_override is not None and step == intervention_step:
            regulator.current_intensity = intervention_intensity_override
            action_set = regulator._get_action_set(intervention_intensity_override)
            effect = InterventionEffect(step=step, actions=action_set)
            for action in action_set:
                regulator._apply_action(action, risk_report.manipulation_risk_score, effect)
            regulator._apply_to_narrative_engine(narrative_engine, risk_report.manipulation_risk_score)
            actions_taken = [a.value for a in action_set]
            print(f"[Step {step}] [REGULATOR] ★ INTERVENTION ({intervention_intensity_override.name}) actions={actions_taken}")
            print(f"  → narrative_cap={regulator.state.narrative_cap:.3f} multiplier={narrative_engine.narrative_strength_multiplier:.3f}")

        # Show key steps
        if step >= 35 and step % 10 == 0 or step in [40, 45, 55, 60, 65, 70]:
            print(f"{step:>4} | {market.price:>7.2f} | {risk_score:>6.3f} | {bubble_score:>6.4f} | {ns_raw:>6.4f} | {ns_eff:>6.4f} | {multiplier:>9.3f} | {regulator.state.narrative_cap:>8.3f} | {[...]
    
    print(f"\nSUMMARY: peak_bubble={peak_bubble:.4f} peak_manip={peak_manip:.4f} high_risk_steps={high_risk_steps}")
    return peak_bubble, peak_manip, high_risk_steps

# Run all three
b, m, h = run_scenario("BASELINE (no intervention)", intervention_step=None, intervention_intensity_override=None)
l_b, l_m, l_h = run_scenario("LIGHT (intervention at step 55)", intervention_step=55, intervention_intensity_override=None)  
s_b, s_m, s_h = run_scenario("STRONG (intervention at step 40)", intervention_step=40, intervention_intensity_override=None)

print(f"\n{'='*60}")
print("FINAL COMPARISON")
print(f"{'='*60}")
print(f"Baseline: peak_bubble={b:.4f} peak_manip={m:.4f} high_risk_steps={h}")
print(f"Light:    peak_bubble={l_b:.4f} peak_manip={l_m:.4f} high_risk_steps={l_h}")
print(f"Strong:   peak_bubble={s_b:.4f} peak_manip={s_m:.4f} high_risk_steps={s_h}")
print(f"\nOrdering check (Strong < Light < Baseline for bubble_risk):")
print(f"  Baseline={b:.4f} Light={l_b:.4f} Strong={s_b:.4f}")
if s_b < l_b < b:
    print("  ✅ PASS: Strong < Light < Baseline")
else:
    print("  ❌ FAIL: Not ordered correctly")
