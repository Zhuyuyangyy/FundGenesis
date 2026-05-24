"""Trace actual narrative_strength, belief_concentration, emotion_amplification values"""
import sys
sys.path.insert(0, '.')

from social.kol_network import KOLNetwork
from narrative.narrative_engine import NarrativeEngine, NarrativeEngineConfig
from narrative.narrative_event import NarrativeEvent, Polarity, NarrativeCategory
from core.emotion_field import EmotionField
from core.market import Market
from core.belief_updater import BeliefUpdater

# Replicate demo setup
kol_network = KOLNetwork()
narrative_engine = NarrativeEngine(NarrativeEngineConfig())
emotion = EmotionField()
market = Market()
belief_updater = BeliefUpdater()

# Create agents (just 10 for speed)
agents = []
for i in range(10):
    from agents.value_investor import ValueInvestorAgent
    agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))

# Setup: same as demo_regulation_baseline
macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]

# Inject at step 25
evt = NarrativeEvent(
    name="龙头股业绩将超预期",
    category=NarrativeCategory.EARNINGS,
    polarity=Polarity.POSITIVE,
    target_sector="tech",
    intensity=0.88,
    credibility=0.82,
    novelty=0.90,
    duration=80,
    source=macro_kols[0].node_id if macro_kols else "test",
)
narrative_engine.inject(evt)

# Simulate ticks 26-55 (bubble formation period)
for step in range(26, 56):
    narrative_engine.tick()
    market.update_price(emotion)
    emotion.decay_toward_neutral(inertia=0.90)
    
    # Update beliefs and emotions like the real demo
    price_change = market.price_change_pct if market.price_history else 0.0
    narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)
    belief_updater.update_all(
        agents=agents, market=market, emotion=emotion,
        kol_network=kol_network, narrative_engine=narrative_engine,
    )
    
    if step % 10 == 0 or step == 55:
        # Compute belief_concentration like ReflexivityMonitor does
        beliefs = [k.belief_state for k in kol_network.get_kols()]
        bc = np.std(beliefs) if len(beliefs) > 1 else 0.0
        
        ns = narrative_engine.narrative_strength()
        ea = emotion.greed + emotion.fear
        print(f"Step {step:3d}: ns={ns:.4f}, bc={bc:.4f}, ea={ea:.4f}, greed={emotion.greed:.3f}, fear={emotion.fear:.3f}")

print()
print(f"Final narrative_strength at step 55: {narrative_engine.narrative_strength():.4f}")
print(f"narrative_strength_multiplier: {narrative_engine.narrative_strength_multiplier:.2f}")