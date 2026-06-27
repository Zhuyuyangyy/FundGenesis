"""Trace actual narrative_engine.narrative_strength values through demo scenario"""
import sys, os
sys.path.insert(0, '.')

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

controller = CreatorController(
    market_config=MarketConfig(
        initial_price=100.0, impact_coefficient=0.20, noise_std=0.008, total_agents=100,
    ),
    emotion_config={"initial_fear": 0.15, "initial_greed": 0.10},
)
market = controller.create_market()
emotion = controller.create_emotion_field()
kol_network = controller.create_kol_network()
propagation = controller.create_propagation_model()
narrative_engine = NarrativeEngine()
trust_engine = TrustEngine(TrustConfig())
trust_bootstrapper = TrustBootstrapper()
belief_updater = BeliefUpdaterV2()
risk_agent = ManipulationRiskAgent()
reflexivity_monitor = ReflexivityMonitor()

agents = []
for i in range(100):
    if i < 10:
        from agents.value_investor import ValueInvestorAgent
        agents.append(ValueInvestorAgent(agent_id="VI_{}".format(i)))
    elif i < 40:
        from agents.trend_follower import TrendFollowerAgent
        agents.append(TrendFollowerAgent(agent_id="TF_{}".format(i)))
    else:
        from agents.emotional_retail import EmotionalRetailAgent
        agents.append(EmotionalRetailAgent(agent_id="ER_{}".format(i)))

macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]

shared_narrative = NarrativeEvent(
    name="龙头股业绩将超预期，AI革命将改变一切",
    category=NarrativeCategory.EARNINGS, polarity=Polarity.POSITIVE, target_sector="tech",
    intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
    source=macro_kols[0].node_id if macro_kols else "macro",
)
narrative_engine.inject(shared_narrative)

print("Tracing narrative_engine.narrative_strength through demo scenario:")
print("-" * 60)

for step in range(26, 56):
    narrative_engine.tick()
    market.update_price(emotion)
    emotion.decay_toward_neutral(inertia=0.90)

    price_change = market.price_change_pct if market.price_history else 0.0
    narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)
    belief_updater.update_all(
        agents=agents, market=market, emotion=emotion,
        kol_network=kol_network, narrative_engine=narrative_engine,
    )

    if step % 10 == 0 or step == 55:
        ns = narrative_engine.narrative_strength()
        beliefs = [k.belief_state for k in kol_network.get_kols()]
        bc = float(np.std(beliefs)) if len(beliefs) > 1 else 0.0
        ea = emotion.greed + emotion.fear
        print("  Step {:3d}: narrative_strength={:.4f}, belief_conc={:.4f}, emotion_amp={:.4f}".format(
            step, ns, bc, ea))

print()
print("narrative_strength at step 55: {:.4f}".format(narrative_engine.narrative_strength()))
print("narrative_strength_multiplier: {:.2f}".format(narrative_engine.narrative_strength_multiplier))

ns_base = narrative_engine.narrative_strength()
for multiplier, label in [(0.60, "Light"), (0.40, "Strong")]:
    narrative_engine.narrative_strength_multiplier = multiplier
    ns_throttled = narrative_engine.narrative_strength()
    print("  {} throttle (multiplier={}): ns={:.4f} ({:.0f}% of baseline)".format(
        label, multiplier, ns_throttled, (ns_throttled/ns_base)*100))