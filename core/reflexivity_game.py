"""
core/reflexivity_game.py
=========================
Reflexivity Game Theory Model (反身性博弈模型)

Implements Soros reflexivity as a multi-agent game:
- Each agent has a belief state and strategy
- Agents observe price movements and narrative signals
- Best-response dynamics drive belief convergence/divergence
- Nash equilibrium analysis detects stable/unstable market regimes

Core framework:
  Agent i's payoff = f(belief_i, market_price, narrative_signal, social_pressure)
  Best response: belief_i* = argmax payoff_i given beliefs of others
  Nash Equilibrium: all agents playing best response simultaneously

Reflexivity emerges when:
  - Agents' beliefs influence price (via trading)
  - Price influences beliefs (via confirmation bias)
  - This creates positive feedback loops (bubbles) or negative loops (crushes)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger('FundGenesis.reflexivity_game')


class GameRegime(Enum):
    """Game-theoretic market regime classification"""
    CONSENSUS_BULL = "consensus_bull"       # All agents bullish - bubble risk
    CONSENSUS_BEAR = "consensus_bear"       # All agents bearish - crash risk
    POLARIZED = "polarized"                 # Agents split - volatile
    CONVERGING = "converging"               # Moving toward consensus
    DIVERGING = "diverging"                 # Moving away from consensus - instability
    EQUILIBRIUM = "equilibrium"             # Stable Nash equilibrium


@dataclass
class GamePayoff:
    """
    Payoff structure for a single agent's belief choice.

    Payoff = α * price_confirmation
           + β * narrative_alignment
           + γ * social_conformity
           - δ * deviation_cost
           - θ * volatility_penalty
    """
    price_confirmation: float = 0.0     # How much price validates belief
    narrative_alignment: float = 0.0    # How much narrative supports belief
    social_conformity: float = 0.0      # Herding benefit
    deviation_cost: float = 0.0         # Cost of being contrarian
    volatility_penalty: float = 0.0     # Uncertainty penalty

    # Weights
    alpha: float = 0.35   # Price confirmation weight
    beta: float = 0.25    # Narrative weight
    gamma: float = 0.20   # Social conformity weight
    delta: float = 0.10   # Deviation cost weight
    theta: float = 0.10   # Volatility penalty weight

    @property
    def total(self) -> float:
        return (
            self.alpha * self.price_confirmation
            + self.beta * self.narrative_alignment
            + self.gamma * self.social_conformity
            - self.delta * self.deviation_cost
            - self.theta * self.volatility_penalty
        )


@dataclass
class AgentGameState:
    """Game-theoretic state for a single agent"""
    agent_id: str
    belief: float = 0.0             # [-1, 1]
    best_response: float = 0.0      # Computed best response belief
    payoff: float = 0.0             # Current payoff
    strategy_stability: float = 0.0  # How stable is the current strategy
    iteration_beliefs: List[float] = field(default_factory=list)


@dataclass
class GameEquilibrium:
    """Result of equilibrium analysis"""
    regime: GameRegime
    nash_distance: float           # How far from Nash equilibrium [0, 1]
    mean_belief: float             # Average market belief
    belief_dispersion: float       # Standard deviation of beliefs
    polarization_index: float      # How polarized the market is [0, 1]
    convergence_rate: float        # How fast beliefs are converging
    is_stable: bool                # Whether equilibrium is stable
    agent_states: List[AgentGameState] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "regime": self.regime.value,
            "nash_distance": round(self.nash_distance, 4),
            "mean_belief": round(self.mean_belief, 4),
            "belief_dispersion": round(self.belief_dispersion, 4),
            "polarization_index": round(self.polarization_index, 4),
            "convergence_rate": round(self.convergence_rate, 4),
            "is_stable": self.is_stable,
        }


class ReflexivityGameModel:
    """
    Multi-agent reflexivity game model.

    Models the market as a repeated game where:
    1. Each agent chooses a belief (strategy) each step
    2. Payoffs depend on price confirmation, narrative, social pressure
    3. Agents update beliefs via best-response dynamics
    4. Reflexivity: beliefs -> trading -> price -> beliefs (feedback loop)

    Usage:
        game = ReflexivityGameModel()
        for step in range(1000):
            equilibrium = game.analyze(
                agents=agents,
                price_change_pct=market.price_change_pct,
                narrative_signal=narrative_engine.narrative_strength(),
                volatility=market.volatility,
            )
            if equilibrium.nash_distance < 0.05:
                print("Near equilibrium")
    """

    def __init__(self,
                 price_weight: float = 0.35,
                 narrative_weight: float = 0.25,
                 social_weight: float = 0.20,
                 max_iterations: int = 10,
                 convergence_threshold: float = 0.01):
        self.price_weight = price_weight
        self.narrative_weight = narrative_weight
        self.social_weight = social_weight
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold

        self._history: List[GameEquilibrium] = []
        self._belief_trajectory: Dict[str, List[float]] = {}

    def compute_best_response(self,
                               agent_belief: float,
                               market_belief_mean: float,
                               price_change_pct: float,
                               narrative_signal: float,
                               volatility: float,
                               sensitivity: float = 0.5,
                               herding: float = 0.3) -> float:
        """
        Compute agent's best-response belief given current market state.

        Best response = weighted combination of:
        - Price confirmation (price validates/invalidates belief)
        - Narrative signal (external information)
        - Social conformity (move toward mean belief)
        - Inertia (stay close to current belief)

        This captures the Soros reflexivity loop:
        belief -> trade -> price -> updated belief
        """
        # Price confirmation: if price moved in belief direction, reinforce
        price_confirm = price_change_pct * np.sign(agent_belief) if abs(agent_belief) > 0.05 else price_change_pct
        price_effect = self.price_weight * price_confirm * 10.0  # Scale up for sensitivity

        # Narrative alignment: how much the narrative supports current belief
        narrative_dir = np.sign(narrative_signal) if abs(narrative_signal) > 0.01 else 0.0
        narrative_effect = self.narrative_weight * narrative_signal * np.sign(
            agent_belief if abs(agent_belief) > 0.05 else 1.0
        )

        # Social conformity: move toward mean belief
        social_effect = self.social_weight * herding * (market_belief_mean - agent_belief)

        # Volatility penalty: high volatility dampens extreme beliefs
        vol_damping = 1.0 - min(volatility * 5.0, 0.5)

        # Inertia: stay close to current belief
        inertia = 0.5 * (1.0 - sensitivity * 0.3)

        # Best response is weighted combination
        raw_br = (
            inertia * agent_belief
            + (1.0 - inertia) * (
                price_effect
                + narrative_effect
                + social_effect
            )
        ) * vol_damping

        return float(np.clip(raw_br, -1.0, 1.0))

    def compute_payoff(self,
                        agent_belief: float,
                        price_change_pct: float,
                        narrative_signal: float,
                        market_belief_mean: float,
                        volatility: float) -> GamePayoff:
        """
        Compute payoff for an agent's current belief choice.
        """
        # Price confirmation: did price movement validate the belief?
        price_confirm = 1.0 - abs(price_change_pct - agent_belief * 0.01)
        price_confirm = max(0.0, min(1.0, price_confirm))

        # Narrative alignment
        if abs(narrative_signal) > 0.01:
            narrative_align = 1.0 - abs(np.sign(narrative_signal) - agent_belief) / 2.0
        else:
            narrative_align = 0.5

        # Social conformity: benefit of being close to mean
        social_conf = 1.0 - abs(agent_belief - market_belief_mean)

        # Deviation cost: cost of being far from mean
        deviation = abs(agent_belief - market_belief_mean)

        return GamePayoff(
            price_confirmation=price_confirm,
            narrative_alignment=narrative_align,
            social_conformity=social_conf,
            deviation_cost=deviation,
            volatility_penalty=volatility * 10.0,
        )

    def analyze(self,
                agents: List,
                price_change_pct: float,
                narrative_signal: float,
                volatility: float) -> GameEquilibrium:
        """
        Perform one-step game-theoretic analysis of the market.

        Returns equilibrium state with:
        - Current regime classification
        - Distance from Nash equilibrium
        - Polarization and convergence metrics
        """
        beliefs = [getattr(a, 'belief', 0.0) for a in agents]
        if not beliefs:
            return GameEquilibrium(
                regime=GameRegime.EQUILIBRIUM,
                nash_distance=0.0, mean_belief=0.0,
                belief_dispersion=0.0, polarization_index=0.0,
                convergence_rate=0.0, is_stable=True,
            )

        beliefs_arr = np.array(beliefs)
        mean_belief = float(np.mean(beliefs_arr))
        std_belief = float(np.std(beliefs_arr))

        # Compute best responses for each agent
        agent_states = []
        new_beliefs = []
        for agent in agents:
            aid = getattr(agent, 'agent_id', str(id(agent)))
            ab = getattr(agent, 'belief', 0.0)
            sens = getattr(getattr(agent, 'config', None), 'emotional_sensitivity', 0.5)
            herd = getattr(getattr(agent, 'config', None), 'herding_coefficient', 0.3)

            br = self.compute_best_response(
                agent_belief=ab,
                market_belief_mean=mean_belief,
                price_change_pct=price_change_pct,
                narrative_signal=narrative_signal,
                volatility=volatility,
                sensitivity=sens,
                herding=herd,
            )

            payoff = self.compute_payoff(
                agent_belief=ab,
                price_change_pct=price_change_pct,
                narrative_signal=narrative_signal,
                market_belief_mean=mean_belief,
                volatility=volatility,
            )

            # Track trajectory
            if aid not in self._belief_trajectory:
                self._belief_trajectory[aid] = []
            self._belief_trajectory[aid].append(ab)

            state = AgentGameState(
                agent_id=aid,
                belief=ab,
                best_response=br,
                payoff=payoff.total,
                strategy_stability=1.0 - abs(br - ab),
            )
            agent_states.append(state)
            new_beliefs.append(br)

        # Nash distance: how far are beliefs from best responses
        br_arr = np.array([s.best_response for s in agent_states])
        nash_distance = float(np.mean(np.abs(beliefs_arr - br_arr)))

        # Polarization: bimodality of beliefs
        polarization = self._compute_polarization(beliefs_arr)

        # Convergence rate: how fast beliefs are moving together
        convergence = self._compute_convergence_rate()

        # Regime classification
        regime = self._classify_regime(
            mean_belief=mean_belief,
            std_belief=std_belief,
            nash_distance=nash_distance,
            polarization=polarization,
            price_change_pct=price_change_pct,
        )

        stability = nash_distance < 0.15 and std_belief < 0.4

        result = GameEquilibrium(
            regime=regime,
            nash_distance=nash_distance,
            mean_belief=mean_belief,
            belief_dispersion=std_belief,
            polarization_index=polarization,
            convergence_rate=convergence,
            is_stable=stability,
            agent_states=agent_states,
        )

        self._history.append(result)
        return result

    def _compute_polarization(self, beliefs: np.ndarray) -> float:
        """
        Compute polarization index using bimodality coefficient.
        Returns [0, 1] where 1 = perfectly polarized (bimodal).
        """
        if len(beliefs) < 2:
            return 0.0
        mean = np.mean(beliefs)
        std = np.std(beliefs)
        if std < 1e-6:
            return 0.0

        # Bimodality coefficient: (skew^2 + 1) / kurtosis
        skew = float(np.mean((beliefs - mean) ** 3) / (std ** 3))
        kurt = float(np.mean((beliefs - mean) ** 4) / (std ** 4))
        if kurt < 1e-6:
            return 0.0

        bc = (skew ** 2 + 1.0) / kurt
        return float(np.clip(bc, 0.0, 1.0))

    def _compute_convergence_rate(self) -> float:
        """Compute how fast beliefs are converging from trajectory history."""
        if len(self._history) < 2:
            return 0.0
        prev = self._history[-2].belief_dispersion
        if prev < 1e-6:
            return 0.0
        current = self._history[-1].belief_dispersion
        return float(np.clip((prev - current) / max(prev, 0.01), -1.0, 1.0))

    def _classify_regime(self,
                          mean_belief: float,
                          std_belief: float,
                          nash_distance: float,
                          polarization: float,
                          price_change_pct: float) -> GameRegime:
        """Classify market regime based on game-theoretic metrics."""
        if nash_distance < 0.10:
            if mean_belief > 0.3:
                return GameRegime.CONSENSUS_BULL
            elif mean_belief < -0.3:
                return GameRegime.CONSENSUS_BEAR
            else:
                return GameRegime.EQUILIBRIUM

        if polarization > 0.6 and std_belief > 0.4:
            return GameRegime.POLARIZED

        if nash_distance > 0.30:
            if std_belief > 0.3:
                return GameRegime.DIVERGING
            return GameRegime.CONVERGING

        if nash_distance < 0.20:
            return GameRegime.CONVERGING

        return GameRegime.DIVERGING

    @property
    def history(self) -> List[GameEquilibrium]:
        return list(self._history)

    def get_trajectory(self, agent_id: str) -> List[float]:
        """Get belief trajectory for a specific agent."""
        return self._belief_trajectory.get(agent_id, [])

    def summary(self) -> dict:
        """Summary of game analysis history."""
        if not self._history:
            return {"steps": 0}
        latest = self._history[-1]
        regime_counts = {}
        for eq in self._history:
            r = eq.regime.value
            regime_counts[r] = regime_counts.get(r, 0) + 1
        return {
            "steps": len(self._history),
            "current_regime": latest.regime.value,
            "nash_distance": round(latest.nash_distance, 4),
            "is_stable": latest.is_stable,
            "regime_distribution": regime_counts,
        }
