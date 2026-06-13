"""
core/risk_propagation.py
=========================
Risk Propagation Engine (风险传播引擎)

Models how financial risk transmits through the agent network:
- Contagion: Risk spreads via social connections (KOL network)
- Amplification: Emotion and herd behavior amplify risk signals
- Cascade: Threshold-based cascade failures (margin calls, panic selling)
- Decentralization: Risk dissipates when disconnected from source

Core transmission model:
  R_i(t+1) = R_i(t) + Σ_j [w_ji * R_j(t) * susceptibility_i]
            + α * emotion_amplification
            + β * herding_pressure
            - γ * natural_decay

Where:
  R_i = risk level for agent i
  w_ji = connection weight from agent j to i
  susceptibility_i = agent i's vulnerability to risk contagion
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger('FundGenesis.risk_propagation')


class RiskSource(Enum):
    """Sources of risk in the system"""
    NARRATIVE_SHOCK = "narrative_shock"         # Sudden negative narrative
    PRICE_CRASH = "price_crash"                 # Rapid price decline
    LIQUIDITY_CRISIS = "liquidity_crisis"       # Buy/sell imbalance
    MANIPULATION = "manipulation"               # Detected manipulation
    EXTERNAL_SHOCK = "external_shock"           # Black swan event
    CASCADE_FAILURE = "cascade_failure"         # Chain reaction


class RiskLevel(Enum):
    """Risk severity levels"""
    SAFE = "safe"           # R < 0.2
    LOW = "low"             # 0.2 <= R < 0.4
    MODERATE = "moderate"   # 0.4 <= R < 0.6
    HIGH = "high"           # 0.6 <= R < 0.8
    CRITICAL = "critical"   # R >= 0.8


@dataclass
class RiskNode:
    """Risk state for a single node in the network"""
    node_id: str
    risk_level: float = 0.0          # [0, 1] current risk
    susceptibility: float = 0.5      # [0, 1] vulnerability to contagion
    recovery_rate: float = 0.05      # Natural risk decay per step
    threshold: float = 0.7           # Cascade trigger threshold
    is_infected: bool = False        # Whether currently in risk state
    infection_step: int = -1         # When risk was first triggered
    connections: List[str] = field(default_factory=list)  # Connected node IDs

    @property
    def risk_category(self) -> RiskLevel:
        if self.risk_level < 0.2:
            return RiskLevel.SAFE
        elif self.risk_level < 0.4:
            return RiskLevel.LOW
        elif self.risk_level < 0.6:
            return RiskLevel.MODERATE
        elif self.risk_level < 0.8:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL


@dataclass
class PropagationEvent:
    """Record of a single risk transmission event"""
    step: int
    source_id: str
    target_id: str
    risk_transmitted: float
    source_risk: float
    target_risk_after: float


@dataclass
class CascadeEvent:
    """Record of a cascade failure"""
    step: int
    trigger_id: str
    affected_ids: List[str]
    total_risk_transmitted: float
    cascade_depth: int


@dataclass
class RiskPropagationReport:
    """Complete risk propagation report for one step"""
    step: int
    system_risk: float                          # Overall system risk [0, 1]
    max_node_risk: float                        # Highest individual risk
    infected_count: int                         # Number of high-risk nodes
    cascade_events: List[CascadeEvent]          # Any cascades this step
    transmission_events: List[PropagationEvent]  # Individual transmissions
    risk_distribution: Dict[str, int]           # Count by risk level
    network_fragility: float                    # How fragile the network is [0, 1]

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "system_risk": round(self.system_risk, 4),
            "max_node_risk": round(self.max_node_risk, 4),
            "infected_count": self.infected_count,
            "cascade_count": len(self.cascade_events),
            "transmission_count": len(self.transmission_events),
            "risk_distribution": self.risk_distribution,
            "network_fragility": round(self.network_fragility, 4),
        }


class RiskPropagationEngine:
    """
    Risk Propagation Engine.

    Models risk transmission through the agent/KOL network using:
    1. Contagion: Risk spreads along social connections
    2. Amplification: Emotion and herding amplify risk
    3. Cascade: Threshold-based chain reactions
    4. Decay: Natural risk dissipation over time

    Usage:
        engine = RiskPropagationEngine()

        # Build network from KOL network
        engine.build_from_kol_network(kol_network, agents)

        # Inject initial risk
        engine.inject_risk("node_id", 0.8, RiskSource.PRICE_CRASH, step=0)

        # Propagate
        for step in range(100):
            report = engine.propagate(
                step=step,
                emotion=emotion,
                price_change_pct=market.price_change_pct,
                volatility=market.volatility,
            )
            if report.system_risk > 0.7:
                print("Systemic risk alert!")
    """

    def __init__(self,
                 contagion_rate: float = 0.3,
                 amplification_factor: float = 1.5,
                 cascade_threshold: float = 0.7,
                 decay_rate: float = 0.05,
                 max_cascade_depth: int = 5):
        self.contagion_rate = contagion_rate
        self.amplification_factor = amplification_factor
        self.cascade_threshold = cascade_threshold
        self.decay_rate = decay_rate
        self.max_cascade_depth = max_cascade_depth

        self._nodes: Dict[str, RiskNode] = {}
        self._history: List[RiskPropagationReport] = []
        self._total_cascades: int = 0

    def build_from_kol_network(self, kol_network, agents: List = None):
        """
        Build risk propagation network from KOL network and agents.

        Maps KOL nodes and agent nodes into the risk graph.
        """
        self._nodes.clear()

        # Add KOL network nodes
        if kol_network is not None:
            for node in kol_network.nodes:
                risk_node = RiskNode(
                    node_id=node.node_id,
                    susceptibility=node.susceptibility,
                    connections=list(node.followers + node.following),
                )
                self._nodes[node.node_id] = risk_node

        # Add agent nodes (linked to their KOL connections)
        if agents is not None:
            for agent in agents:
                aid = getattr(agent, 'agent_id', str(id(agent)))
                sens = getattr(getattr(agent, 'config', None), 'emotional_sensitivity', 0.5)
                risk_node = RiskNode(
                    node_id=f"agent_{aid}",
                    susceptibility=sens,
                    recovery_rate=0.03 + 0.02 * sens,  # More sensitive = slower recovery
                )
                self._nodes[risk_node.node_id] = risk_node

            # Link agents to KOL network (random assignment to micro KOLs)
            if kol_network is not None:
                micro_ids = [n.node_id for n in kol_network.get_kols()
                             if hasattr(n, 'tier') and n.tier.value == 'micro']
                for agent in agents:
                    aid = getattr(agent, 'agent_id', str(id(agent)))
                    agent_node_id = f"agent_{aid}"
                    if micro_ids and agent_node_id in self._nodes:
                        # Connect to 1-2 micro KOLs
                        targets = np.random.choice(micro_ids, size=min(2, len(micro_ids)), replace=False)
                        for t in targets:
                            self._nodes[agent_node_id].connections.append(t)
                            if t in self._nodes:
                                self._nodes[t].connections.append(agent_node_id)

    def inject_risk(self, node_id: str, magnitude: float,
                    source: RiskSource, step: int = 0):
        """
        Inject initial risk into a specific node.
        """
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.risk_level = float(np.clip(magnitude, 0.0, 1.0))
            node.is_infected = node.risk_level >= self.cascade_threshold * 0.5
            if node.is_infected and node.infection_step < 0:
                node.infection_step = step
            logger.debug(f"Injected risk {magnitude:.2f} into {node_id}")

    def inject_systemic_risk(self, magnitude: float, step: int = 0,
                              target_fraction: float = 0.3):
        """
        Inject risk into a fraction of the network (systemic shock).
        """
        n_target = max(1, int(len(self._nodes) * target_fraction))
        targets = np.random.choice(
            list(self._nodes.keys()),
            size=min(n_target, len(self._nodes)),
            replace=False,
        )
        for tid in targets:
            # Vary magnitude by susceptibility
            susc = self._nodes[tid].susceptibility
            actual = magnitude * (0.5 + 0.5 * susc)
            self.inject_risk(tid, actual, RiskSource.EXTERNAL_SHOCK, step)

    def propagate(self,
                  step: int,
                  emotion=None,
                  price_change_pct: float = 0.0,
                  volatility: float = 0.0,
                  narrative_risk: float = 0.0) -> RiskPropagationReport:
        """
        Execute one step of risk propagation.

        Args:
            step: Current simulation step
            emotion: EmotionField for amplification
            price_change_pct: Price change for crash detection
            volatility: Market volatility for amplification
            narrative_risk: Risk from negative narratives
        """
        transmissions = []
        cascades = []

        # Compute emotion amplification
        emotion_amp = 1.0
        if emotion is not None:
            fear_amp = getattr(emotion, 'fear', 0.3) * self.amplification_factor
            uncertainty_amp = getattr(emotion, 'uncertainty', 0.3) * 0.5
            emotion_amp = 1.0 + fear_amp + uncertainty_amp

        # Price crash amplification
        price_crash_amp = 1.0
        if price_change_pct < -0.02:
            price_crash_amp = 1.0 + abs(price_change_pct) * 10.0

        # Step 1: Natural decay for all nodes
        for node in self._nodes.values():
            node.risk_level *= (1.0 - node.recovery_rate)
            if node.risk_level < 0.01:
                node.risk_level = 0.0
                node.is_infected = False

        # Step 2: Contagion - risk spreads along connections
        risk_deltas: Dict[str, float] = {nid: 0.0 for nid in self._nodes}

        for node in self._nodes.values():
            if node.risk_level < 0.05:
                continue

            for conn_id in node.connections:
                if conn_id not in self._nodes:
                    continue
                target = self._nodes[conn_id]

                # Transmission = source_risk * contagion_rate * target_susceptibility * emotion_amp
                transmission = (
                    node.risk_level
                    * self.contagion_rate
                    * target.susceptibility
                    * emotion_amp
                    * 0.5  # Base damping
                )

                # Connection weight (higher for KOL -> retail)
                conn_weight = 1.0
                if not node.node_id.startswith('agent_') and target.node_id.startswith('agent_'):
                    conn_weight = 1.5  # KOL -> agent gets higher weight
                transmission *= conn_weight

                if transmission > 0.01:
                    risk_deltas[conn_id] += transmission
                    transmissions.append(PropagationEvent(
                        step=step,
                        source_id=node.node_id,
                        target_id=conn_id,
                        risk_transmitted=transmission,
                        source_risk=node.risk_level,
                        target_risk_after=min(1.0, target.risk_level + transmission),
                    ))

        # Step 3: Apply contagion deltas
        for nid, delta in risk_deltas.items():
            if nid in self._nodes:
                self._nodes[nid].risk_level = float(np.clip(
                    self._nodes[nid].risk_level + delta, 0.0, 1.0
                ))
                if self._nodes[nid].risk_level >= self.cascade_threshold * 0.5:
                    self._nodes[nid].is_infected = True
                    if self._nodes[nid].infection_step < 0:
                        self._nodes[nid].infection_step = step

        # Step 4: Cascade detection
        cascade_affected = set()
        for node in self._nodes.values():
            if (node.risk_level >= self.cascade_threshold
                    and node.is_infected
                    and step - node.infection_step > 2):
                # This node is cascading - amplify risk to all connections
                cascade_targets = []
                for conn_id in node.connections:
                    if conn_id in self._nodes:
                        target = self._nodes[conn_id]
                        cascade_risk = node.risk_level * 0.5 * target.susceptibility
                        if cascade_risk > 0.1:
                            target.risk_level = float(np.clip(
                                target.risk_level + cascade_risk, 0.0, 1.0
                            ))
                            cascade_targets.append(conn_id)
                            cascade_affected.add(conn_id)

                if cascade_targets:
                    cascades.append(CascadeEvent(
                        step=step,
                        trigger_id=node.node_id,
                        affected_ids=cascade_targets,
                        total_risk_transmitted=sum(
                            node.risk_level * 0.5 * self._nodes[c].susceptibility
                            for c in cascade_targets if c in self._nodes
                        ),
                        cascade_depth=1,
                    ))
                    self._total_cascades += 1

        # Step 5: External risk injection from narrative/price
        if narrative_risk > 0.1 or price_change_pct < -0.03:
            # Inject into high-susceptibility nodes
            for node in self._nodes.values():
                if node.susceptibility > 0.6:
                    ext_risk = 0.0
                    if narrative_risk > 0.1:
                        ext_risk += narrative_risk * 0.3 * node.susceptibility
                    if price_change_pct < -0.03:
                        ext_risk += abs(price_change_pct) * 2.0 * node.susceptibility
                    node.risk_level = float(np.clip(node.risk_level + ext_risk, 0.0, 1.0))

        # Compute report
        risk_levels = [n.risk_level for n in self._nodes.values()]
        system_risk = float(np.mean(risk_levels)) if risk_levels else 0.0
        max_risk = float(np.max(risk_levels)) if risk_levels else 0.0
        infected = sum(1 for n in self._nodes.values() if n.is_infected)

        # Risk distribution
        dist = {"safe": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0}
        for n in self._nodes.values():
            dist[n.risk_category.value] += 1

        # Network fragility: fraction of highly connected nodes that are infected
        high_degree_nodes = sorted(
            self._nodes.values(),
            key=lambda n: len(n.connections),
            reverse=True
        )[:max(1, len(self._nodes) // 10)]
        fragility = float(np.mean([
            n.risk_level for n in high_degree_nodes
        ])) if high_degree_nodes else 0.0

        report = RiskPropagationReport(
            step=step,
            system_risk=system_risk,
            max_node_risk=max_risk,
            infected_count=infected,
            cascade_events=cascades,
            transmission_events=transmissions,
            risk_distribution=dist,
            network_fragility=fragility,
        )

        self._history.append(report)
        return report

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def history(self) -> List[RiskPropagationReport]:
        return list(self._history)

    def get_node_risk(self, node_id: str) -> float:
        """Get risk level for a specific node."""
        node = self._nodes.get(node_id)
        return node.risk_level if node else 0.0

    def get_high_risk_nodes(self, threshold: float = 0.6) -> List[RiskNode]:
        """Get all nodes with risk above threshold."""
        return [n for n in self._nodes.values() if n.risk_level >= threshold]

    def summary(self) -> dict:
        """Summary of risk propagation state."""
        if not self._history:
            return {"steps": 0, "nodes": len(self._nodes)}
        latest = self._history[-1]
        return {
            "steps": len(self._history),
            "nodes": len(self._nodes),
            "system_risk": round(latest.system_risk, 4),
            "max_node_risk": round(latest.max_node_risk, 4),
            "infected_count": latest.infected_count,
            "total_cascades": self._total_cascades,
            "network_fragility": round(latest.network_fragility, 4),
        }
