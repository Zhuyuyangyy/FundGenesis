"""Diagnose order_imbalance and bubble_risk with actual submit_order calls"""
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
reflexivity_monitor = ReflexivityMonitor()

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
influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
micro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MICRO]

evt = NarrativeEvent(
    name="龙头股业绩将超预期",
    category=NarrativeCategory.EARNINGS, polarity=Polarity.POSITIVE, target_sector="tech",
    intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
    source=macro_kols[0].node_id if macro_kols else "macro",
)
narrative_engine.inject(evt)
propagation.inject_narrative(evt)

print("Step-by-step with order_imbalance and bubble_risk:")
print("-" * 100)
print("{:>4} | {:>7} | {:>8} | {:>8} | {:>6} | {:>6} | {:>6} | {:>7} | {:>8}".format(
    "Step", "Price", "buy_vol", "sell_vol", "oi", "cf", "bubble_risk", "manip_risk", "fomo"))
print("-" * 100)

for step in range(26, 61):
    narrative_engine.tick()
    propagation.step()
    belief_updater.update_all(
        agents=agents, market=market, emotion=emotion,
        kol_network=kol_network, narrative_engine=narrative_engine,
    )
    price_change = market.price_change_pct if market.price_history else 0.0
    narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)

    # Place orders (like real demo)
    for agent in agents:
        action = agent.decide(market.get_snapshot(), emotion)
        volume = agent.get_trade_volume()
        market.submit_order(agent.agent_id, action.value, volume)

    market.update_price(emotion)
    emotion.decay_toward_neutral(inertia=0.90)

    if step % 5 == 0 or step in [25, 33, 45, 55]:
        ns = narrative_engine.narrative_strength()
        beliefs = [k.belief_state for k in kol_network.get_kols()]
        bc = float(np.std(beliefs)) if len(beliefs) > 1 else 0.0
        ea = emotion.greed + emotion.fear
        vm = float(np.clip(market.volatility * 10, 0.0, 1.0)) if hasattr(market, 'volatility') else 0.0
        oi = market.order_imbalance
        cf = 0.1 + 0.9 * min(abs(oi) / 5.0, 1.0)
        nf = min(ns / 2.0, 1.0)
        bb = bc * 30.0
        eb = ea * 4.0
        risk = bb * eb * vm * cf * (0.5 + 0.5 * nf)
        
        manip_risk = 0.087  # approximate from demo (manipulation_risk is stable at 0.087 pre-FOMO)
        fomo = 0.0
        
        print("{:>4} | {:>7.2f} | {:>8.2f} | {:>8.2f} | {:>6.3f} | {:>6.3f} | {:>8.4f} | {:>7.4f} | {:>6.3f}".format(
            step, market.price, market.buy_volume, market.sell_volume, oi, cf, risk, manip_risk, fomo))