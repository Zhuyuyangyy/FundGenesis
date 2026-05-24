"""
src/agents/regulator_agent.py
==============================
RegulatorAgent V0.1 — Simplified SCI 2区 Regulation

3 intervention strategies:
  1. narrative_throttle  — reduce propagation speed by 50%
  2. kol_downweight      — reduce suspicious KOL trust by 50%
  3. risk_warning        — public alert reduces FOMO by 30%

Usage:
    regulator = RegulatorAgent()
    new_state = regulator.apply_intervention("narrative_throttle", market_state)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import copy


class InterventionStrategy(Enum):
    NARRATIVE_THROTTLE = "narrative_throttle"
    KOL_DOWNWEIGHT = "kol_downweight"
    RISK_WARNING = "risk_warning"
    NO_ACTION = "no_action"


# How strongly each strategy affects each market dimension
_STRATEGY_EFFECTS = {
    InterventionStrategy.NARRATIVE_THROTTLE: {
        "propagation_speed": 0.50,   # 50% reduction
        "kol_trust": 0.0,
        "fomo": 0.0,
    },
    InterventionStrategy.KOL_DOWNWEIGHT: {
        "propagation_speed": 0.0,
        "kol_trust": 0.50,           # 50% reduction
        "fomo": 0.0,
    },
    InterventionStrategy.RISK_WARNING: {
        "propagation_speed": 0.0,
        "kol_trust": 0.0,
        "fomo": 0.30,                # 30% FOMO reduction
    },
}


@dataclass
class InterventionEffect:
    strategy: str
    propagation_speed_mult: float   # multiplier on speed (1.0 = no change)
    kol_trust_mult: float
    fomo_reduction: float           # absolute reduction (0.0-1.0)


class RegulatorAgent:
    """
    Simple regulator for SCI 2区 compliance.

    Usage:
        regulator = RegulatorAgent()
        new_state = regulator.apply_intervention("narrative_throttle", market_state)

        # Multi-intervention
        results = regulator.apply_interventions(
            ["narrative_throttle", "risk_warning"], market_state
        )
    """

    def __init__(self):
        self._active_interventions: List[InterventionStrategy] = []
        self._intervention_log: List[Dict[str, Any]] = []

    def apply_intervention(
        self,
        strategy: str,
        market_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply a single intervention strategy to market_state.
        Returns a modified copy (does not mutate original).
        """
        try:
            strat = InterventionStrategy(strategy)
        except ValueError:
            strat = InterventionStrategy.NO_ACTION

        if strat == InterventionStrategy.NO_ACTION:
            return copy.deepcopy(market_state)

        self._active_interventions = [strat]
        effect = _STRATEGY_EFFECTS.get(strat, {})

        # Build new state
        new_state = copy.deepcopy(market_state)

        # propagation_speed
        if effect.get("propagation_speed", 0) > 0:
            cur = new_state.get("propagation_speed", 1.0)
            new_state["propagation_speed"] = cur * (1.0 - effect["propagation_speed"])

        # kol_trust (can be stored as avg or per-KOL dict)
        if effect.get("kol_trust", 0) > 0:
            kol_trust = new_state.get("kol_trust", {})
            if isinstance(kol_trust, dict):
                new_state["kol_trust"] = {
                    k: v * (1.0 - effect["kol_trust"])
                    for k, v in kol_trust.items()
                }
            else:
                new_state["kol_trust"] = kol_trust * (1.0 - effect["kol_trust"])

        # fomo reduction
        if effect.get("fomo", 0) > 0:
            cur_fomo = new_state.get("fomo_level", new_state.get("fomo", 0.0))
            new_state["fomo"] = max(0.0, cur_fomo - effect["fomo"])

        # Log
        self._intervention_log.append({
            "strategy": strategy,
            "effect": {k: round(v, 4) for k, v in effect.items()},
            "applied_to": list(market_state.keys()),
        })

        return new_state

    def apply_interventions(
        self,
        strategies: List[str],
        market_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply multiple intervention strategies in sequence.
        """
        state = copy.deepcopy(market_state)
        for s in strategies:
            state = self.apply_intervention(s, state)
        return state

    def get_intervention_log(self) -> List[Dict[str, Any]]:
        return list(self._intervention_log)

    def clear_log(self):
        self._intervention_log.clear()