"""Quick diagnostic of bubble_risk with narrative_factor differentiation"""
import sys
sys.path.insert(0, '.')
import numpy as np

from monitor.reflexivity_monitor import ReflexivityMonitor

monitor = ReflexivityMonitor()

# Typical bubble period: bc=0.04, ea=0.53, vm=0.07 (volatility input)
# capital_imbalance=2.0 → capital_factor=0.4
# narrative_strength: Baseline=1.2 (full), Light=0.72 (multiplier=0.60), Strong=0.48 (multiplier=0.40)

params = [
    ("Baseline (ns=1.2)", 0.04, 0.53, 0.07, 1.2, 2.0),
    ("Light    (ns=0.72)", 0.04, 0.53, 0.07, 0.72, 2.0),
    ("Strong   (ns=0.48)", 0.04, 0.53, 0.07, 0.48, 2.0),
]

print("bubble_risk differentiation (k=1.0):")
print("-" * 50)
for label, bc, ea, vm, ns, ci in params:
    risk = monitor._compute_bubble_risk(bc, ea, 0.0, ns, ci, vm)
    narrative_factor = min(ns/2.0, 1.0)
    print(f"  {label}: bubble_risk={risk:.4f}, narrative_factor={narrative_factor:.3f}")

print()
print("Component breakdown for Baseline:")
bc, ea, vm, ns, ci = 0.04, 0.53, 0.07, 1.2, 2.0
belief_boost = bc * 30.0
emotion_boost = ea * 4.0
capital_factor = min(abs(ci)/5.0, 1.0)
narrative_factor = min(ns/2.0, 1.0)
vm_val = float(np.clip(vm * 10, 0.0, 1.0))
print(f"  belief_boost={belief_boost:.4f} (bc={bc})")
print(f"  emotion_boost={emotion_boost:.4f} (ea={ea})")
print(f"  volatility_momentum={vm_val:.4f} (vm={vm})")
print(f"  capital_factor={capital_factor:.4f} (ci={ci})")
print(f"  narrative_factor={narrative_factor:.4f} (ns={ns})")
print(f"  (0.5+0.5*nf)={0.5+0.5*narrative_factor:.4f}")
product = belief_boost * emotion_boost * vm_val * capital_factor * (0.5 + 0.5 * narrative_factor)
print(f"  risk = {belief_boost:.3f}*{emotion_boost:.3f}*{vm_val:.3f}*{capital_factor:.3f}*{0.5+0.5*narrative_factor:.3f} = {product:.4f}")