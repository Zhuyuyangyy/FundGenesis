# Core Layer
# Eager imports (no circular issues)
from .market_environment import MarketEnvironment, MarketSnapshot
from .emotion_field import EmotionField
from .creator_controller import CreatorController, MarketConfig, ShockConfig

# Lazy import for belief_updater_v2 (avoids circular: narrative_engine -> emotion_field -> belief_updater_v2 -> narrative_engine)
def _lazy_belief_updater():
    from .belief_updater_v2 import BeliefUpdaterV2, BeliefUpdaterConfig
    return BeliefUpdaterV2, BeliefUpdaterConfig

def __getattr__(name):
    if name in ("BeliefUpdaterV2", "BeliefUpdaterConfig"):
        return _lazy_belief_updater()[0 if name == "BeliefUpdaterV2" else 1]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "MarketEnvironment", "MarketSnapshot",
    "EmotionField",
    "CreatorController", "MarketConfig", "ShockConfig",
    "BeliefUpdaterV2", "BeliefUpdaterConfig",
]
