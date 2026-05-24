"""Trace KOL receive_exposure and belief propagation directly"""
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

print("=== Inject narrative at step 25 ===")
evt = NarrativeEvent(
    name="龙头股业绩将超预期",
    category=NarrativeCategory.EARNINGS, polarity=Polarity.POSITIVE, target_sector="tech",
    intensity=0.88, credibility=0.82, novelty=0.90, duration=80,
    source=macro_kols[0].node_id if macro_kols else "macro",
)
propagation.inject_narrative(evt)

print("After inject_narrative (step 25):")
for kol in macro_kols[:2]:
    print("  {}: belief={:.4f}, narrative_exposure={:.4f}, susceptibility={:.1f}".format(
        kol.node_id[:8], kol.belief_state, kol.narrative_exposure, kol.susceptibility))
for kol in influencer_kols[:3]:
    print("  {}: belief={:.4f}, narrative_exposure={:.4f}".format(
        kol.node_id[:8], kol.belief_state, kol.narrative_exposure))

print()
print("=== Propagation steps ===")
for step in range(26, 56):
    propagation.step()
    if step % 10 == 0 or step == 55:
        beliefs = [k.belief_state for k in kol_network.get_kols()]
        bc = float(np.std(beliefs)) if len(beliefs) > 1 else 0.0
        print("Step {:3d}: belief_conc={:.4f}".format(step, bc))
        for kol in macro_kols[:2]:
            print("  macro {}: belief={:.4f}, exposure={:.4f}".format(
                kol.node_id[:8], kol.belief_state, kol.narrative_exposure))
        for kol in influencer_kols[:2]:
            print("  inf   {}: belief={:.4f}, exposure={:.4f}".format(
                kol.node_id[:8], kol.belief_state, kol.narrative_exposure))
        for kol in micro_kols[:2]:
            print("  micro {}: belief={:.4f}, exposure={:.4f}".format(
                kol.node_id[:8], kol.belief_state, kol.narrative_exposure))

print()
print("Final belief_concentration: {:.4f}".format(bc))