"""
reflexmarket/core/world_state.py
=================================
Unified simulation state container.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldState:
    step: int = 0
    seed: int | None = None
    market: Any = None
    emotion: Any = None
    narrative_engine: Any = None
    kol_network: Any = None
    trust_engine: Any = None
    belief_updater: Any = None
    propagation: Any = None
    reflexivity_monitor: Any = None
    risk_agent: Any = None
    regulator: Any = None
    agents: list[Any] = field(default_factory=list)
    prev_risk_score: float = 0.0
    current_risk_score: float = 0.0
    current_bubble_risk: float = 0.0
    current_panic_risk: float = 0.0
    current_manipulation_risk: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    metrics_history: list[dict[str, Any]] = field(default_factory=list)
    active_narrative: Any = None
    injection_done: dict[int, bool] = field(default_factory=dict)
    regulation_mode: str = "baseline"

    def snapshot(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "price": self.market.price if self.market else None,
            "risk_score": self.current_risk_score,
            "bubble_risk": self.current_bubble_risk,
            "regulation_mode": self.regulation_mode,
        }
