"""Trace KOL belief propagation step by step through demo scenario"""
import sys, os
sys.path.insert(0, '.')

import numpy as np
from social.kol_network import KOLNetwork, KOLTier, KOLNode
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from social.propagation_model import PropagationModel

kol_network = KOLNetwork().build_default_network(n_macro=2, n_influencer=5, n_micro=10, n_retail=100)
propagation = PropagationModel(kol_network)

macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
micro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MICRO]

print("KOL network: {} macro, {} influencer, {} micro".format(
    len(macro_kols), len(influencer_kols), len(micro_kols)))
print()

# Inject narrative at step 25
evt = NarrativeEvent(
    name="龙头股业绩将超预期",
    category=NarrativeCategory.EARNINGS, polarity=Polarity.POSITIVE, target_sector="tech",
    intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
    source=macro_kols[0].node_id if macro_kols else "macro",
)
propagation.inject_narrative(evt)

print("After inject_narrative (step 25):")
for kol in macro_kols[:2]:
    print("  {} (macro): belief={:.4f}, exposure={:.4f}".format(
        kol.node_id[:8], kol.belief_state, kol.narrative_exposure))

# Simulate propagation steps 26-55
for step in range(26, 56):
    propagation.step()
    if step % 10 == 0 or step == 55:
        beliefs = [k.belief_state for k in kol_network.get_kols()]
        bc = float(np.std(beliefs)) if len(beliefs) > 1 else 0.0
        macro_beliefs = [k.belief_state for k in macro_kols]
        inf_beliefs = [k.belief_state for k in influencer_kols]
        micro_beliefs = [k.belief_state for k in micro_kols]
        print("Step {:3d}: bc={:.4f}, macro_belief={:.4f}, inf_belief={:.4f}, micro_belief={:.4f}".format(
            step, bc, 
            np.mean(macro_beliefs) if macro_beliefs else 0,
            np.mean(inf_beliefs) if inf_beliefs else 0,
            np.mean(micro_beliefs) if micro_beliefs else 0))
        # Print top KOL beliefs
        for kol in macro_kols[:2]:
            print("         {}: belief={:.4f}, exposure={:.4f}".format(
                kol.node_id[:8], kol.belief_state, kol.narrative_exposure))

print()
print("Final belief_concentration (std):", bc)
print("All KOL beliefs:")
for kol in kol_network.get_kols()[:5]:
    print("  {}: belief={:.4f}".format(kol.node_id[:8], kol.belief_state))