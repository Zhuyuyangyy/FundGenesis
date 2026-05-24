# Social Layer
# Eager imports for kol_network (no circular issues)
from .kol_network import KOLNetwork, KOLNode, KOLTier

# Lazy imports for propagation models (avoid circular via narrative -> core -> belief_updater_v2)
def _lazy_propagation_imports():
    from .propagation_model import PropagationModel
    from .propagation_model_v2 import TrustAwarePropagationModel
    return PropagationModel, TrustAwarePropagationModel

def __getattr__(name):
    if name == "PropagationModel":
        return _lazy_propagation_imports()[0]
    if name == "TrustAwarePropagationModel":
        return _lazy_propagation_imports()[1]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "KOLNetwork", "KOLNode", "KOLTier",
    "PropagationModel", "TrustAwarePropagationModel",
]
