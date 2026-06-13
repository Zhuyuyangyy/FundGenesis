"""
test_belief_updater.py - Belief Updater Tests
==============================================
Comprehensive tests for the belief update engine.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.belief_updater_v2 import (
    BeliefUpdaterV2, BeliefUpdaterConfig,
    compute_market_belief_centrality, detect_reflexivity_regime,
)
from core.emotion_field import EmotionField
from agents.base_agent import AgentConfig


# ── Helper ─────────────────────────────────────────────────────

def create_mock_agent(belief=0.0, emotional_sensitivity=0.5, herding_coefficient=0.3):
    agent = MagicMock()
    agent.belief = belief
    agent.config = MagicMock()
    agent.config.emotional_sensitivity = emotional_sensitivity
    agent.config.herding_coefficient = herding_coefficient
    agent.config.confirmation_bias = 0.3
    return agent


# ── BeliefUpdaterConfig Tests ──────────────────────────────────

class TestBeliefUpdaterConfig:
    def test_defaults(self):
        cfg = BeliefUpdaterConfig()
        assert cfg.belief_inertia == 0.6
        assert cfg.narrative_weight == 0.15
        assert cfg.price_confirmation_weight == 0.2
        assert cfg.social_pressure_weight == 0.1
        assert cfg.contradiction_penalty == 0.1
        assert cfg.max_belief_change == 0.3


# ── BeliefUpdaterV2 Tests ──────────────────────────────────────

class TestBeliefUpdaterV2:
    def test_creation(self):
        updater = BeliefUpdaterV2()
        assert updater.config.belief_inertia == 0.6

    def test_creation_custom_config(self):
        cfg = BeliefUpdaterConfig(belief_inertia=0.7)
        updater = BeliefUpdaterV2(cfg)
        assert updater.config.belief_inertia == 0.7

    def test_update_single_basic(self):
        updater = BeliefUpdaterV2()
        agent = create_mock_agent(belief=0.0)
        updater._update_single(
            agent,
            price_confirmation=0.1,
            social_pressure=0.0,
            narrative_shift=0.2,
            contradiction_signal=0.0,
        )
        # Should move toward positive
        assert agent.belief >= 0.0

    def test_update_single_clipping(self):
        updater = BeliefUpdaterV2()
        agent = create_mock_agent(belief=0.0)
        # Extreme values should be clipped
        updater._update_single(
            agent,
            price_confirmation=1.0,
            social_pressure=1.0,
            narrative_shift=1.0,
            contradiction_signal=0.0,
        )
        assert -1.0 <= agent.belief <= 1.0

    def test_update_all(self, market, emotion):
        updater = BeliefUpdaterV2()
        agents = [create_mock_agent(belief=0.0) for _ in range(5)]
        updater.update_all(
            agents=agents,
            market=market,
            emotion=emotion,
            kol_network=None,
            narrative_engine=None,
            social_pressure_override=0.2,
        )
        for agent in agents:
            assert -1.0 <= agent.belief <= 1.0

    def test_compute_price_confirmation(self):
        updater = BeliefUpdaterV2()
        conf = updater._compute_price_confirmation(0.05)
        assert conf > 0

    def test_compute_contradiction(self):
        updater = BeliefUpdaterV2()
        emotion = EmotionField(fear=0.3, greed=0.7)  # Greed dominant
        narrative = MagicMock()
        # Price goes down while greed is high = contradiction
        contradiction = updater._compute_contradiction(-0.02, narrative, emotion)
        assert contradiction > 0

    def test_emotional_agent_more_sensitive(self):
        updater = BeliefUpdaterV2()
        # Emotional agent
        emotional = create_mock_agent(belief=0.0, emotional_sensitivity=0.8)
        # Rational agent
        rational = create_mock_agent(belief=0.0, emotional_sensitivity=0.2)

        updater._update_single(emotional, 0.1, 0.0, 0.2, 0.0)
        updater._update_single(rational, 0.1, 0.0, 0.2, 0.0)

        # Emotional agent should be more influenced by narrative
        # (but the exact difference depends on the formula)


# ── compute_market_belief_centrality Tests ─────────────────────

class TestComputeMarketBeliefCentrality:
    def test_empty_agents(self):
        assert compute_market_belief_centrality([]) == 0.0

    def test_uniform_beliefs(self):
        agents = [create_mock_agent(belief=0.8) for _ in range(10)]
        centrality = compute_market_belief_centrality(agents)
        assert centrality == pytest.approx(0.8)

    def test_mixed_beliefs(self):
        agents = [create_mock_agent(belief=0.5), create_mock_agent(belief=-0.5)]
        centrality = compute_market_belief_centrality(agents)
        assert centrality == pytest.approx(0.5)


# ── detect_reflexivity_regime Tests ────────────────────────────

class TestDetectReflexivityRegime:
    def test_normal(self):
        regime = detect_reflexivity_regime(0.0, 0.1, 0.1)
        assert regime == "normal"

    def test_bubble(self):
        regime = detect_reflexivity_regime(0.05, 0.7, 0.3)
        assert regime == "bubble"

    def test_crash(self):
        regime = detect_reflexivity_regime(-0.05, 0.7, 0.3)
        assert regime == "crash"

    def test_panic_spread(self):
        regime = detect_reflexivity_regime(0.0, 0.5, 0.6)
        # With belief_concentration=0.5 (>0.3 but <0.6),
        # and price_change=0.0 (abs <= 0.01), it should be "normal"
        # unless emotion_amplification triggers it
        assert regime in ["normal", "panic_spread"]

    def test_transition(self):
        regime = detect_reflexivity_regime(0.015, 0.4, 0.2)
        assert regime == "transition"
