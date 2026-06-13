"""
test_reflexivity_game.py
========================
Tests for the Reflexivity Game Theory Model (core/reflexivity_game.py)
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.reflexivity_game import (
    ReflexivityGameModel, GameRegime, GamePayoff, GameEquilibrium, AgentGameState,
)


def create_mock_agents(n=20, beliefs=None):
    agents = []
    for i in range(n):
        agent = MagicMock()
        agent.agent_id = f"agent_{i:03d}"
        agent.belief = beliefs[i] if beliefs and i < len(beliefs) else np.random.uniform(-0.5, 0.5)
        agent.config = MagicMock()
        agent.config.emotional_sensitivity = np.random.uniform(0.2, 0.8)
        agent.config.herding_coefficient = np.random.uniform(0.1, 0.7)
        agents.append(agent)
    return agents


class TestGamePayoff:
    def test_payoff_positive(self):
        payoff = GamePayoff(
            price_confirmation=0.8, narrative_alignment=0.7,
            social_conformity=0.6, deviation_cost=0.1, volatility_penalty=0.1,
        )
        assert payoff.total > 0

    def test_payoff_negative_on_high_deviation(self):
        payoff = GamePayoff(
            price_confirmation=0.1, narrative_alignment=0.1,
            social_conformity=0.1, deviation_cost=0.9, volatility_penalty=0.9,
        )
        assert payoff.total < 0

    def test_payoff_weights_applied(self):
        payoff = GamePayoff(
            price_confirmation=1.0, narrative_alignment=0.0,
            social_conformity=0.0, deviation_cost=0.0, volatility_penalty=0.0,
        )
        expected = 0.35 * 1.0
        assert abs(payoff.total - expected) < 0.01


class TestReflexivityGameModel:
    def test_creation(self):
        model = ReflexivityGameModel()
        assert model.price_weight == 0.35
        assert model.narrative_weight == 0.25
        assert model.social_weight == 0.20

    def test_custom_params(self):
        model = ReflexivityGameModel(price_weight=0.5, narrative_weight=0.3, social_weight=0.2, max_iterations=5)
        assert model.price_weight == 0.5

    def test_best_response_bounded(self):
        model = ReflexivityGameModel()
        for _ in range(100):
            br = model.compute_best_response(
                agent_belief=np.random.uniform(-1, 1),
                market_belief_mean=np.random.uniform(-1, 1),
                price_change_pct=np.random.uniform(-0.05, 0.05),
                narrative_signal=np.random.uniform(-1, 1),
                volatility=np.random.uniform(0.01, 0.1),
            )
            assert -1.0 <= br <= 1.0

    def test_best_response_positive_feedback(self):
        model = ReflexivityGameModel()
        br = model.compute_best_response(
            agent_belief=0.5, market_belief_mean=0.5,
            price_change_pct=0.03, narrative_signal=0.5, volatility=0.01,
        )
        assert br >= 0.0

    def test_best_response_negative_feedback(self):
        model = ReflexivityGameModel()
        br = model.compute_best_response(
            agent_belief=0.5, market_belief_mean=0.5,
            price_change_pct=-0.03, narrative_signal=-0.5, volatility=0.01,
        )
        assert br < 0.5

    def test_analyze_returns_equilibrium(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=10)
        result = model.analyze(agents=agents, price_change_pct=0.01, narrative_signal=0.3, volatility=0.02)
        assert isinstance(result, GameEquilibrium)
        assert isinstance(result.regime, GameRegime)
        assert 0.0 <= result.nash_distance <= 1.0

    def test_consensus_bull_regime(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=10, beliefs=[0.8] * 10)
        result = model.analyze(agents=agents, price_change_pct=0.02, narrative_signal=0.5, volatility=0.01)
        assert result.mean_belief > 0.3

    def test_consensus_bear_regime(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=10, beliefs=[-0.8] * 10)
        result = model.analyze(agents=agents, price_change_pct=-0.02, narrative_signal=-0.5, volatility=0.01)
        assert result.mean_belief < -0.3

    def test_polarized_regime(self):
        model = ReflexivityGameModel()
        beliefs = [0.9] * 10 + [-0.9] * 10
        agents = create_mock_agents(n=20, beliefs=beliefs)
        result = model.analyze(agents=agents, price_change_pct=0.0, narrative_signal=0.0, volatility=0.05)
        assert result.belief_dispersion > 0.3

    def test_empty_agents(self):
        model = ReflexivityGameModel()
        result = model.analyze(agents=[], price_change_pct=0.0, narrative_signal=0.0, volatility=0.0)
        assert result.regime == GameRegime.EQUILIBRIUM
        assert result.nash_distance == 0.0

    def test_history_tracking(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=5)
        model.analyze(agents, 0.01, 0.1, 0.02)
        model.analyze(agents, 0.02, 0.2, 0.03)
        assert len(model.history) == 2

    def test_summary(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=5)
        model.analyze(agents, 0.01, 0.1, 0.02)
        summary = model.summary()
        assert "steps" in summary
        assert "current_regime" in summary

    def test_trajectory_tracking(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=3)
        model.analyze(agents, 0.01, 0.1, 0.02)
        trajectory = model.get_trajectory("agent_000")
        assert len(trajectory) == 1

    def test_as_dict(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=5)
        result = model.analyze(agents, 0.01, 0.1, 0.02)
        d = result.as_dict()
        assert "regime" in d
        assert "nash_distance" in d
        assert isinstance(d["regime"], str)


class TestEdgeCases:
    def test_extreme_volatility_dampens_beliefs(self):
        model = ReflexivityGameModel()
        br_low = model.compute_best_response(0.5, 0.5, 0.02, 0.3, 0.01)
        br_high = model.compute_best_response(0.5, 0.5, 0.02, 0.3, 0.2)
        assert abs(br_high) <= abs(br_low) + 0.1

    def test_zero_narrative(self):
        model = ReflexivityGameModel()
        br = model.compute_best_response(0.0, 0.0, 0.0, 0.0, 0.0)
        assert isinstance(br, float)

    def test_all_same_beliefs(self):
        model = ReflexivityGameModel()
        agents = create_mock_agents(n=10, beliefs=[0.5] * 10)
        result = model.analyze(agents, 0.01, 0.1, 0.02)
        assert result.belief_dispersion < 0.01
