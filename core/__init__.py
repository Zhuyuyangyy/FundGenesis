# Core Layer
# Eager imports (no circular issues)
from .market_environment import MarketEnvironment, MarketSnapshot
from .emotion_field import EmotionField
from .creator_controller import CreatorController, MarketConfig, ShockConfig

# Lazy imports to avoid circular dependencies
def _lazy_belief_updater():
    from .belief_updater_v2 import BeliefUpdaterV2, BeliefUpdaterConfig
    return BeliefUpdaterV2, BeliefUpdaterConfig

def _lazy_reflexivity_game():
    from .reflexivity_game import ReflexivityGameModel, GameRegime, GameEquilibrium
    return ReflexivityGameModel, GameRegime, GameEquilibrium

def _lazy_risk_propagation():
    from .risk_propagation import RiskPropagationEngine, RiskSource, RiskLevel
    return RiskPropagationEngine, RiskSource, RiskLevel

def _lazy_simulation_runner():
    from .simulation_runner import SimulationRunner, SimulationConfig, SimulationResult
    return SimulationRunner, SimulationConfig, SimulationResult

def __getattr__(name):
    if name in ("BeliefUpdaterV2", "BeliefUpdaterConfig"):
        return _lazy_belief_updater()[0 if name == "BeliefUpdaterV2" else 1]
    if name in ("ReflexivityGameModel", "GameRegime", "GameEquilibrium"):
        idx = ["ReflexivityGameModel", "GameRegime", "GameEquilibrium"].index(name)
        return _lazy_reflexivity_game()[idx]
    if name in ("RiskPropagationEngine", "RiskSource", "RiskLevel"):
        idx = ["RiskPropagationEngine", "RiskSource", "RiskLevel"].index(name)
        return _lazy_risk_propagation()[idx]
    if name in ("SimulationRunner", "SimulationConfig", "SimulationResult"):
        idx = ["SimulationRunner", "SimulationConfig", "SimulationResult"].index(name)
        return _lazy_simulation_runner()[idx]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "MarketEnvironment", "MarketSnapshot",
    "EmotionField",
    "CreatorController", "MarketConfig", "ShockConfig",
    "BeliefUpdaterV2", "BeliefUpdaterConfig",
    "ReflexivityGameModel", "GameRegime", "GameEquilibrium",
    "RiskPropagationEngine", "RiskSource", "RiskLevel",
    "SimulationRunner", "SimulationConfig", "SimulationResult",
]
