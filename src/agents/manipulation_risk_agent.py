"""
src/agents/manipulation_risk_agent.py
======================================
ManipulationRiskAgent V0.1 — Simplified SCI 2区 Detection

Detects 3 key manipulation patterns:
  1. coordinated_kol   — 3+ KOLs post same narrative within 3 steps
  2. fomo             — belief jump > 0.3 in one step
  3. divergence       — price up but narrative negative (or vice versa)

Output: {
    "manipulation_risk_score": 0.0-1.0,
    "alert_type": "coordinated"|"fomo"|"divergence"|"none"
}
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class AlertType(Enum):
    COORDINATED = "coordinated"
    FOMO = "fomo"
    DIVERGENCE = "divergence"
    NONE = "none"


@dataclass
class ManipulationRiskReport:
    manipulation_risk_score: float  # 0.0-1.0
    alert_type: AlertType             # primary alert classification
    details: Dict[str, Any]           # per-pattern scores


class ManipulationRiskAgent:
    """
    Simple manipulation risk detector for SCI 2区 compliance.

    Usage:
        agent = ManipulationRiskAgent()
        report = agent.evaluate(market_state)
    """

    def __init__(self):
        self._last_belief: Optional[float] = None
        self._kol_narrative_history: Dict[str, List[tuple]] = {}  # kol_id -> [(step, narrative_id), ...]

    def evaluate(self, market_state: Dict[str, Any]) -> ManipulationRiskReport:
        """
        Evaluate manipulation risk from market state.

        Args:
            market_state: dict with keys:
                - step: int
                - kol_network: KOLNetwork or dict of KOLs
                - belief: float  (current avg belief, -1 to 1)
                - price_change_pct: float  (e.g. 0.05 = +5%)
                - narrative_polarity: float  (-1 negative, +1 positive)
                - price_direction: str ("up" or "down")

        Returns:
            ManipulationRiskReport
        """
        step = market_state.get("step", 0)
        belief = market_state.get("belief", 0.0)
        price_change_pct = market_state.get("price_change_pct", 0.0)
        narrative_polarity = market_state.get("narrative_polarity", 0.0)
        kol_network = market_state.get("kol_network", {})

        scores = {}
        alert_types = []

        # ── 1. Coordinated KOL detection ──────────────────
        coord_score = self._detect_coordinated(kol_network, step)
        scores["coordinated"] = coord_score
        if coord_score > 0.5:
            alert_types.append(AlertType.COORDINATED)

        # ── 2. FOMO detection ──────────────────────────────
        fomo_score = self._detect_fomo(belief)
        scores["fomo"] = fomo_score
        if fomo_score > 0.5:
            alert_types.append(AlertType.FOMO)

        # ── 3. Price-narrative divergence ───────────────────
        div_score = self._detect_divergence(price_change_pct, narrative_polarity)
        scores["divergence"] = div_score
        if div_score > 0.5:
            alert_types.append(AlertType.DIVERGENCE)

        # ── Weighted composite score ──────────────────────
        manipulation_risk_score = (
            0.45 * scores["coordinated"]
            + 0.30 * scores["fomo"]
            + 0.25 * scores["divergence"]
        )
        manipulation_risk_score = max(0.0, min(1.0, manipulation_risk_score))

        # Primary alert: highest-scoring active pattern
        primary = max(alert_types, default=AlertType.NONE)

        return ManipulationRiskReport(
            manipulation_risk_score=round(manipulation_risk_score, 4),
            alert_type=primary,
            details={
                "coordinated_score": round(scores["coordinated"], 4),
                "fomo_score": round(scores["fomo"], 4),
                "divergence_score": round(scores["divergence"], 4),
            },
        )

    def _detect_coordinated(self, kol_network, step: int) -> float:
        """
        Coordinated KOL: same narrative posted by 3+ KOLs within 3 steps.
        Returns score 0.0-1.0.
        """
        if not kol_network:
            return 0.0

        # kol_network can be a KOLNetwork object or a dict
        if hasattr(kol_network, "get_kols"):
            kols = kol_network.get_kols()
        elif isinstance(kol_network, dict):
            kols = kol_network.get("kols", [])
        else:
            kols = []

        narratives_by_step: Dict[int, List[str]] = {}
        for kol in kols:
            recent = getattr(kol, "recent_narratives", [])
            # recent_narratives: list of (step, narrative_id)
            for (s, nid) in recent[-3:]:
                if step - s <= 3:
                    narratives_by_step.setdefault(nid, []).append(kol.node_id if hasattr(kol, "node_id") else str(kol))

        # Score: 3+ KOLs sharing same narrative within 3 steps
        max_score = 0.0
        for nid, kol_ids in narratives_by_step.items():
            unique_kols = set(kol_ids)
            if len(unique_kols) >= 4:
                max_score = 1.0
            elif len(unique_kols) >= 3:
                max_score = max(max_score, 0.80)

        return max_score

    def _detect_fomo(self, current_belief: float) -> float:
        """
        FOMO: belief jump > 0.3 in one step.
        Returns score 0.0-1.0.
        """
        if self._last_belief is None:
            self._last_belief = current_belief
            return 0.0

        jump = abs(current_belief - self._last_belief)
        self._last_belief = current_belief

        if jump > 0.4:
            return 1.0
        elif jump > 0.3:
            return 0.75
        elif jump > 0.2:
            return 0.40
        elif jump > 0.15:
            return 0.20
        return 0.0

    def _detect_divergence(self, price_change_pct: float, narrative_polarity: float) -> float:
        """
        Divergence: price up but narrative negative (or vice versa).
        Returns score 0.0-1.0.
        """
        # Normalise
        price_dir = 1 if price_change_pct > 0 else (-1 if price_change_pct < 0 else 0)
        # narrative_polarity: -1 (negative) to +1 (positive)
        narr_dir = 1 if narrative_polarity > 0.1 else (-1 if narrative_polarity < -0.1 else 0)

        if price_dir == 0 or narr_dir == 0:
            return 0.0

        if price_dir == narr_dir:
            return 0.0  # aligned, not divergent

        # Divergent: score by magnitude
        magnitude = abs(price_change_pct) + abs(narrative_polarity)
        if magnitude > 0.3:
            return 0.85
        elif magnitude > 0.15:
            return 0.50
        return 0.20

    def reset(self):
        self._last_belief = None
        self._kol_narrative_history.clear()