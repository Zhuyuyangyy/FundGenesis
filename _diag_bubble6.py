"""Trace narrative_engine.narrative_strength via NarrativeRegistry directly"""
import sys, os
sys.path.insert(0, '.')

from narrative.narrative_event import NarrativeEvent, NarrativeRegistry, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine

# Build registry with exactly one event matching demo conditions
registry = NarrativeRegistry()
evt = NarrativeEvent(
    name="龙头股业绩将超预期，AI革命将改变一切",
    category=NarrativeCategory.EARNINGS,
    polarity=Polarity.POSITIVE,
    target_sector="tech",
    intensity=0.88,
    credibility=0.82,
    novelty=0.90,
    duration=80,
    source="macro_kol",
)
registry.add(evt)

# Check active count
print("Registry active count:", len(registry.active))
print("Event effective_intensity:", evt.effective_intensity)
print("Event credibility:", evt.credibility)

# Raw sum
raw_sum = sum(e.effective_intensity * e.credibility for e in registry.active)
print("Raw narrative_strength sum:", raw_sum)

# What NarrativeEngine returns (with multiplier=1.0)
ne = NarrativeEngine()
ne.inject(evt)
print("\nNarrativeEngine.narrative_strength():", ne.narrative_strength())
print("NarrativeEngine.multiplier:", ne.narrative_strength_multiplier)

# Now see what tick does over 30 steps (simulate 30 steps of decay)
for t in range(1, 31):
    expired = registry.tick_all()
    if t % 10 == 0:
        active_count = len(registry.active)
        ns = ne.narrative_strength()
        print("  tick {:2d}: active={}, ns={:.4f}, effective_intensity={:.4f}".format(
            t, active_count, ns, evt.effective_intensity))