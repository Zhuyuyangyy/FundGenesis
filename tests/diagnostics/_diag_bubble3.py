"""Quick diagnostic: trace narrative_engine.narrative_strength() actual value"""
import sys
sys.path.insert(0, '.')

from social.kol_network import KOLNetwork, KOLTier
from narrative.narrative_engine import NarrativeEngine, NarrativeEngineConfig
from narrative.narrative_event import NarrativeEvent, Polarity, NarrativeCategory

# Create engine
ne = NarrativeEngine(NarrativeEngineConfig())

# Simulate step=55 scenario: inject strong narrative (same as demo)
macro_kol_id = "macro_test"
evt = NarrativeEvent(
    name="龙头股业绩将超预期",
    category=NarrativeCategory.EARNINGS,
    polarity=Polarity.POSITIVE,
    target_sector="tech",
    intensity=0.88,
    credibility=0.82,
    novelty=0.90,
    duration=80,
    source=macro_kol_id,
)
ne.inject(evt)

print(f"After inject (tick 0): narrative_strength={ne.narrative_strength():.4f}, multiplier={ne.narrative_strength_multiplier:.2f}")

# Simulate ticks passing (bubble formation)
for tick in range(1, 56):
    ne.tick()

ns = ne.narrative_strength()
print(f"After tick {tick} (step ~55): narrative_strength={ns:.4f}")

# Simulate throttle (Light: multiplier=0.60)
ne.narrative_strength_multiplier = 0.60
ns_throttled = ne.narrative_strength()
print(f"After throttle (0.60): narrative_strength={ns_throttled:.4f}")

# Simulate throttle (Strong: multiplier=0.40)  
ne.narrative_strength_multiplier = 0.40
ns_strong = ne.narrative_strength()
print(f"After throttle (0.40): narrative_strength={ns_strong:.4f}")

print()
print(f"Raw narrative_strength (no throttle): {ns:.4f}")
print(f"Throttled (0.60): {ns_throttled:.4f}")
print(f"Throttled (0.40): {ns_strong:.4f}")
print(f"Suppression: {ns_throttled/ns:.1f}x (Light), {ns_strong/ns:.1f}x (Strong)")