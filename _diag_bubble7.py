"""Instrumented demo that prints real belief_concentration, emotion_amplification, narrative_strength at step 55"""
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
    emotion_config={"initial_fear": 0.15, "initial_greed": 0.60,
                    "fear_inertia": 0.92, "greed_inertia": 0.92},
)
market = controller.setup_market()
emotion = controller.setup_emotion()
belief_updater = BeliefUpdaterV2()

kol_network = KOLNetwork().build_default_network(n_macro=2, n_influencer=5, n_micro=10, n_retail=100)
narrative_engine = NarrativeEngine()
trust_engine = TrustEngine(TrustConfig())
trust_bootstrapper = TrustBootstrapper()
risk_agent = ManipulationRiskAgent()
reflexivity_monitor = ReflexivityMonitor()

macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
micro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MICRO]

from agents.value_investor import ValueInvestorAgent
from agents.trend_follower import TrendFollowerAgent
from agents.emotional_retail import EmotionalRetailAgent
agents = []
for i in range(100):
    if i < 10:
        agents.append(ValueInvestorAgent(agent_id="VI_{}".format(i)))
    elif i < 40:
        agents.append(TrendFollowerAgent(agent_id="TF_{}".format(i)))
    else:
        agents.append(EmotionalRetailAgent(agent_id="ER_{}".format(i)))

# Inject narrative at step 25
shared_narrative = NarrativeEvent(
    name="龙头股业绩将超预期，AI革命将改变一切",
    category=NarrativeCategory.EARNINGS, polarity=Polarity.POSITIVE, target_sector="tech",
    intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
    source=macro_kols[0].node_id if macro_kols else "macro",
)
narrative_engine.inject(shared_narrative)
propagation = PropagationModel(kol_network)

# Simulate steps 26-56
for step in range(26, 57):
    narrative_engine.tick()
    market.update_price(emotion)
    emotion.decay_toward_neutral(inertia=0.90)

    price_change = market.price_change_pct if market.price_history else 0.0
    narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)
    belief_updater.update_all(
        agents=agents, market=market, emotion=emotion,
        kol_network=kol_network, narrative_engine=narrative_engine,
    )

    if step == 55:
        # Record values at step 55
        ns = narrative_engine.narrative_strength()
        beliefs = [k.belief_state for k in kol_network.get_kols()]
        bc = float(np.std(beliefs)) if len(beliefs) > 1 else 0.0
        ea = emotion.greed + emotion.fear
        volatility = market.volatility if hasattr(market, 'volatility') else 0.0
        price_change_val = market.price_change_pct if market.price_history else 0.0

        print("Values at step 55 (bubble peak):")
        print("  narrative_strength: {:.4f}".format(ns))
        print("  belief_concentration (std of beliefs): {:.4f}".format(bc))
        print("  emotion_amplification (greed+fear): {:.4f}".format(ea))
        print("  emotion.greed: {:.4f}, emotion.fear: {:.4f}".format(emotion.greed, emotion.fear))
        print("  volatility: {:.4f}".format(volatility))
        print("  price_change_pct: {:.4f}".format(price_change_val))
        print("  capital_imbalance: {:.4f}".format(market.order_imbalance if hasattr(market, 'order_imbalance') else 0.0))

        # Compute bubble_risk manually
        vm = float(np.clip(volatility * 10, 0.0, 1.0))
        ci = abs(market.order_imbalance) if hasattr(market, 'order_imbalance') else 0.0
        capital_factor = min(ci / 5.0, 1.0)
        narrative_factor = min(ns / 2.0, 1.0)
        belief_boost = bc * 30.0
        emotion_boost = ea * 4.0

        print()
        print("Bubble risk components at step 55:")
        print("  belief_boost = {:.4f} * 30 = {:.4f}".format(bc, belief_boost))
        print("  emotion_boost = {:.4f} * 4 = {:.4f}".format(ea, emotion_boost))
        print("  volatility_momentum = clip({:.4f} * 10, 0, 1) = {:.4f}".format(volatility, vm))
        print("  capital_factor = min({:.4f}/5, 1) = {:.4f}".format(ci, capital_factor))
        print("  narrative_factor = min({:.4f}/2, 1) = {:.4f}".format(ns, narrative_factor))

        risk = belief_boost * emotion_boost * vm * capital_factor * (0.5 + 0.5 * narrative_factor)
        print("  risk = {:.4f} * {:.4f} * {:.4f} * {:.4f} * {:.4f} = {:.4f}".format(
            belief_boost, emotion_boost, vm, capital_factor, 0.5 + 0.5 * narrative_factor, risk))

        # Also show what happens with throttle
        for multiplier, label in [(0.60, "Light"), (0.40, "Strong")]:
            ns_throttled = ns * multiplier
            nf_throttled = min(ns_throttled / 2.0, 1.0)
            risk_throttled = belief_boost * emotion_boost * vm * capital_factor * (0.5 + 0.5 * nf_throttled)
            print("  {} throttle: ns={:.4f}, narrative_factor={:.4f}, bubble_risk={:.4f}".format(
                label, ns_throttled, nf_throttled, risk_throttled))