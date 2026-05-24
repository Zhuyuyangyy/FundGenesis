"""Compute bubble_risk with fixed belief + volatility formula"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.creator_controller import CreatorController, MarketConfig
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_engine import NarrativeEngine
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from monitor.reflexivity_monitor import ReflexivityMonitor
from risk.manipulation_risk_agent import ManipulationRiskAgent
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from agents.emotional_retail import EmotionalRetailAgent
from agents.trend_follower import TrendFollowerAgent
from agents.value_investor import ValueInvestorAgent
import json, numpy as np

def run_scenario(intensity: str, n_steps: int = 200):
    controller = CreatorController(
        market_config=MarketConfig(initial_price=100.0, impact_coefficient=0.20, noise_std=0.008, total_agents=100),
        emotion_config={'initial_fear': 0.15, 'initial_greed': 0.60, 'fear_inertia': 0.92, 'greed_inertia': 0.92}
    )
    market = controller.setup_market()
    emotion = controller.setup_emotion()
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
    
    for step in range(n_steps):
        # Narrative injection at step 30
        if step == 30 and macro_kols:
            shared_narrative = NarrativeEvent(
                name="tech_bubble_v2", category=NarrativeCategory.EARNINGS,
                polarity=Polarity.POSITIVE, target_sector="tech",
                intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
                source=macro_kols[0].node_id,
            )
            narrative_engine.inject(shared_narrative)
            propagation.inject_narrative(shared_narrative)
            risk_agent.record_kol_spread(shared_narrative._id, macro_kols[0].node_id)
        
        if step == 33 and influencer_kols and shared_narrative:
            for inf in influencer_kols[:3]:
                risk_agent.record_kol_spread(shared_narrative._id, inf.node_id)
        
        if step == 38 and micro_kols and shared_narrative:
            for mic in micro_kols[:4]:
                risk_agent.record_kol_spread(shared_narrative._id, mic.node_id)
        
        if step == 48 and shared_narrative:
            risk_agent.record_price_feedback(shared_narrative._id, 0.03, 0.72, step)
        
        if step == 55:
            risk_agent.record_fomo_signal(0.78, 0.82, 0.70, step)
        
        # Tick
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
        
        # Log metrics
        bc = kol_network.belief_concentration()
        ea = max(emotion.greed, emotion.fear)
        volatility = market.volatility
        ns = narrative_engine.narrative_strength()
        
        reflexivity_monitor.observe(
            market, kol_network, emotion, narrative_engine,
            risk_agent, agents, trust_engine, bc, ea, ns,
        )
        
        br = reflexivity_monitor._compute_bubble_risk(
            belief_concentration=bc,
            emotion_amplification=ea,
            price_change_pct=price_change,
            narrative_strength=ns,
            capital_imbalance=market.order_imbalance,
            volatility=volatility,
        )
        
        reflexivity_monitor.record_step(step, market, kol_network, emotion, narrative_engine, risk_agent)
    
    # Compute summary
    log = reflexivity_monitor.get_summary()
    manip_scores = [e['manipulation_risk_score'] for e in reflexivity_monitor.metrics_log]
    bubble_scores = [e['bubble_risk_score'] for e in reflexivity_monitor.metrics_log]
    high_risk_manip = sum(1 for s in manip_scores if s >= 0.25)
    
    return {
        "intensity": intensity,
        "peak_manipulation_risk": max(manip_scores) if manip_scores else 0,
        "peak_bubble_risk": max(bubble_scores) if bubble_scores else 0,
        "high_risk_steps_manip": high_risk_manip,
        "steps_above_05": sum(1 for s in bubble_scores if s >= 0.5),
        "steps_above_03": sum(1 for s in bubble_scores if s >= 0.3),
        "volatility_range": (min(bubble_scores), max(bubble_scores)),
    }

# Run three scenarios
print("Running Baseline (no intervention)...")
baseline = run_scenario("baseline", 200)
print(f"Baseline: peak_bubble={baseline['peak_bubble_risk']:.4f}, peak_manip={baseline['peak_manipulation_risk']:.4f}, high_risk={baseline['high_risk_steps_manip']}")

print("Running Light intervention...")
from risk.regulator_agent import RegulatorAgent, InterventionIntensity
reg_light = RegulatorAgent(intensity=InterventionIntensity.LIGHT)
# Light will be handled by RegulatorAgent integration in a full run
# For now just check bubble risk calculation with volatility-based formula

print("Done.")