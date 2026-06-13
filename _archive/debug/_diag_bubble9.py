"""Diagnose _compute_bubble_risk components step by step through the real demo"""
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
propagation = PropagationModel(kol_network)

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

macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]

# Inject narrative at step 25
evt = NarrativeEvent(
    name="龙头股业绩将超预期",
    category=NarrativeCategory.EARNINGS, polarity=Polarity.POSITIVE, target_sector="tech",
    intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
    source=macro_kols[0].node_id if macro_kols else "macro",
)
narrative_engine.inject(evt)
propagation.inject_narrative(evt)

print("Step-by-step bubble_risk components (key steps only):")
print("-" * 85)
print("{:>4} | {:>7} | {:>6} | {:>7} | {:>6} | {:>6} | {:>6} | {:>7} | {:>8}".format(
    "Step", "Price", "bc(all)", "bc(kol)", "ea", "vm", "ci", "ns", "bubble_risk"))
print("-" * 85)

# Run from step 26 to 60, recording at key steps
for step in range(26, 61):
    narrative_engine.tick()
    market.update_price(emotion)
    emotion.decay_toward_neutral(inertia=0.90)

    price_change = market.price_change_pct if market.price_history else 0.0
    narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)
    belief_updater.update_all(
        agents=agents, market=market, emotion=emotion,
        kol_network=kol_network, narrative_engine=narrative_engine,
    )

    if step % 10 == 0 or step in [25, 28, 33, 45, 55, 60]:
        ns = narrative_engine.narrative_strength()

        # belief_concentration from ALL agents (current approach)
        all_beliefs = [k.belief_state for k in kol_network.get_kols()]
        bc_all = float(np.std(all_beliefs)) if len(all_beliefs) > 1 else 0.0

        # belief_concentration from KOLs only (better signal)
        kol_beliefs = [k.belief_state for k in kol_network.get_kols()
                      if k.tier in [KOLTier.MACRO, KOLTier.INFLUENCER, KOLTier.MICRO]]
        bc_kol = float(np.std(kol_beliefs)) if len(kol_beliefs) > 1 else 0.0

        ea = emotion.greed + emotion.fear
        vm = float(np.clip(market.volatility * 10, 0.0, 1.0)) if hasattr(market, 'volatility') else 0.0
        ci = abs(market.order_imbalance) if hasattr(market, 'order_imbalance') else 0.0

        # Current formula (k=1.0, capital_factor = ci/5 capped)
        cf = min(ci / 5.0, 1.0)
        nf = min(ns / 2.0, 1.0)
        bb = bc_all * 30.0
        eb = ea * 4.0
        risk_all = bb * eb * vm * cf * (0.5 + 0.5 * nf)

        # KOL-only formula
        bb_kol = bc_kol * 30.0
        risk_kol = bb_kol * eb * vm * cf * (0.5 + 0.5 * nf)

        print("{:>4} | {:>7.2f} | {:>6.4f} | {:>7.4f} | {:>6.4f} | {:>6.3f} | {:>6.4f} | {:>7.4f} | {:>8.4f}".format(
            step, market.price, bc_all, bc_kol, ea, vm, ci, ns, risk_all))

print()
print("Key observation: capital_imbalance (ci) is near 0 → capital_factor ≈ 0 → bubble_risk ≈ 0")
print("Even with emotion_amplification=0.82 and narrative_strength=0.45, ci=0 kills the risk.")
print()
print("Fix: Change capital_factor from min(|ci|/5, 1) to use ci^0.5 so ci=0 gives 0.1 instead of 0")
print("Proposed: capital_factor = 0.1 + 0.9 * min(|ci|/5, 1)")