"""Trace KOL belief propagation with full chain"""
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
import numpy as np

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

print("Tracing KOL belief propagation through demo scenario")
print("=" * 70)

for step in range(60):
    # Inject narrative events
    if step == 25 and macro_kols:
        shared_narrative = NarrativeEvent(
            name="bubble_narrative", category=NarrativeCategory.EARNINGS,
            polarity=Polarity.POSITIVE, target_sector="tech",
            intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
            source=macro_kols[0].node_id,
        )
        narrative_engine.inject(shared_narrative)
        propagation.inject_narrative(shared_narrative)
        risk_agent.record_kol_spread(shared_narrative._id, macro_kols[0].node_id)
        print(f"\n[Step {step}] WAVE1: Macro KOL injects narrative")
        print(f"  Narrative intensity={shared_narrative.intensity}, source={macro_kols[0].node_id}")

    if step == 28 and influencer_kols and shared_narrative:
        for inf in influencer_kols[:3]:
            risk_agent.record_kol_spread(shared_narrative._id, inf.node_id)
        print(f"\n[Step {step}] WAVE2: 3 Influencers amplify")

    if step == 33 and micro_kols and shared_narrative:
        for mic in micro_kols[:4]:
            risk_agent.record_kol_spread(shared_narrative._id, mic.node_id)
        print(f"\n[Step {step}] WAVE3: 4 Micro KOLs cross-tier")

    if step == 45 and shared_narrative:
        risk_agent.record_price_feedback(shared_narrative._id, 0.03, 0.72, step)
        print(f"\n[Step {step}] PRICE_VALIDATION: price confirms narrative")

    if step == 55:
        risk_agent.record_fomo_signal(0.78, 0.82, 0.70, step)
        print(f"\n[Step {step}] FOMO: retail buy_ratio=0.78")

    # Propagation step
    propagation.step()
    narrative_engine.tick()

    # Belief update
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

    # Show KOL beliefs at key steps
    if step in [24, 25, 26, 28, 30, 33, 40, 45, 55, 58]:
        print(f"\n  Step {step}:")
        stats = kol_network.belief_statistics()
        print(f"    belief_concentration={stats['belief_concentration']:.4f}")
        print(f"    emotion.greed={emotion.greed:.3f}, fear={emotion.fear:.3f}")
        print(f"    market.price={market.price:.2f}, volatility={market.volatility:.4f}")

        # Show top KOLs
        all_kols = list(kol_network.get_kols())
        top_kols = sorted(all_kols, key=lambda k: abs(k.belief_state), reverse=True)[:5]
        for k in top_kols:
            print(f"    KOL {k.node_id}: tier={k.tier.value}, belief={k.belief_state:.4f}, "
                  f"exposure={k.narrative_exposure:.3f}, susc={k.susceptibility}, "
                  f"influence={k.influence_score:.3f}")

        # Check narrative strength
        ns = narrative_engine.narrative_strength()
        print(f"    narrative_strength={ns:.3f}")

print("\n" + "=" * 70)
print("DIAGNOSIS: Where does belief_state stay near 0?")
print()
# Find nodes with non-zero belief
all_nodes = list(kol_network._nodes.values())
non_zero = [n for n in all_nodes if abs(n.belief_state) > 0.01]
print(f"Nodes with |belief_state| > 0.01: {len(non_zero)} / {len(all_nodes)}")
if non_zero:
    for n in non_zero[:5]:
        print(f"  {n.node_id}: tier={n.tier.value}, belief={n.belief_state:.4f}")
else:
    print("  ALL nodes have belief_state near 0!")
    print()
    print("  Root cause: receive_exposure calls are not happening OR")
    print("  belief_shift is too small (exposure * 0.3 * 0.1 * direction = exposure * 0.03)")
    print(f"  Each receive_exposure call adds at most 0.03 * exposure to belief_state")
    print(f"  Need ~33 exposures to reach belief_state=1.0")
    print()
    print("  Susceptibility of different tiers:")
    for tier in [KOLTier.MACRO, KOLTier.INFLUENCER, KOLTier.MICRO, KOLTier.RETAIL]:
        nodes = [n for n in all_nodes if n.tier == tier]
        if nodes:
            print(f"  {tier.value}: {len(nodes)} nodes, avg_susc={np.mean([n.susceptibility for n in nodes]):.2f}")