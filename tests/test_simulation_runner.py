"""
test_simulation_runner.py
==========================
Tests for the Simulation Runner (core/simulation_runner.py)
"""

import pytest
import numpy as np
import json
import tempfile
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.simulation_runner import (
    SimulationRunner, SimulationConfig, SimulationResult, SimulationStepResult,
)


# ── SimulationConfig Tests ─────────────────────────────────────

class TestSimulationConfig:
    def test_defaults(self):
        """Default config should have reasonable values"""
        cfg = SimulationConfig()
        assert cfg.n_steps == 200
        assert cfg.initial_price == 100.0
        assert cfg.n_retail == 50
        assert cfg.n_trend == 20
        assert cfg.n_value == 10
        assert cfg.enable_reflexivity_game is True
        assert cfg.enable_risk_propagation is True

    def test_custom_config(self):
        """Should accept custom parameters"""
        cfg = SimulationConfig(
            n_steps=100,
            n_retail=10,
            n_trend=5,
            n_value=3,
            seed=42,
        )
        assert cfg.n_steps == 100
        assert cfg.seed == 42


# ── SimulationRunner Tests ─────────────────────────────────────

class TestSimulationRunner:
    @pytest.fixture
    def small_config(self):
        """Small config for fast tests"""
        return SimulationConfig(
            n_steps=10,
            n_retail=5,
            n_trend=3,
            n_value=2,
            seed=42,
            quiet=True,
            enable_reflexivity_game=True,
            enable_risk_propagation=True,
            enable_regulator=True,
        )

    @pytest.fixture
    def minimal_config(self):
        """Minimal config for fastest tests"""
        return SimulationConfig(
            n_steps=5,
            n_retail=3,
            n_trend=1,
            n_value=1,
            seed=42,
            quiet=True,
            enable_reflexivity_game=False,
            enable_risk_propagation=False,
            enable_regulator=False,
        )

    def test_creation(self, small_config):
        """Should create runner"""
        runner = SimulationRunner(small_config)
        assert runner.config == small_config

    def test_run_returns_result(self, small_config):
        """run() should return SimulationResult"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        assert isinstance(result, SimulationResult)
        assert result.config == small_config

    def test_run_step_count(self, small_config):
        """Should produce correct number of steps"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        assert len(result.steps) == small_config.n_steps

    def test_price_changes(self, small_config):
        """Price should change during simulation"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        prices = [s.price for s in result.steps]
        # Price should not be constant (due to noise)
        assert max(prices) != min(prices)

    def test_emotion_evolution(self, small_config):
        """Emotions should evolve during simulation"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        fears = [s.fear for s in result.steps]
        greeds = [s.greed for s in result.steps]
        # Should have some variation
        assert max(fears) - min(fears) > 0.0 or max(greeds) - min(greeds) > 0.0

    def test_agent_decisions_recorded(self, small_config):
        """Agent decisions should be recorded"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        for step in result.steps:
            total = step.buy_count + step.sell_count + step.hold_count
            assert total == small_config.n_retail + small_config.n_trend + small_config.n_value

    def test_reflexivity_metrics_present(self, small_config):
        """Reflexivity metrics should be computed"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        for step in result.steps:
            assert 0.0 <= step.reflexivity_index <= 1.0
            assert 0.0 <= step.bubble_risk <= 1.0
            assert isinstance(step.regime, str)

    def test_game_theory_metrics(self, small_config):
        """Game theory metrics should be present when enabled"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        for step in result.steps:
            assert step.game_regime is not None
            assert step.nash_distance is not None
            assert step.polarization is not None

    def test_risk_propagation_metrics(self, small_config):
        """Risk propagation metrics should be present when enabled"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        for step in result.steps:
            assert step.system_risk is not None
            assert step.cascade_count is not None

    def test_minimal_run(self, minimal_config):
        """Minimal config should run without errors"""
        runner = SimulationRunner(minimal_config)
        result = runner.run()
        assert len(result.steps) == 5
        assert result.duration_seconds > 0

    def test_narrative_injection(self):
        """Should handle narrative events"""
        cfg = SimulationConfig(
            n_steps=20,
            n_retail=3,
            n_trend=1,
            n_value=1,
            seed=42,
            quiet=True,
            narrative_events=[
                {
                    "name": "Test Narrative",
                    "category": "fintech",
                    "polarity": "positive",
                    "intensity": 0.7,
                    "timing": 5,
                    "duration": 10,
                }
            ],
        )
        runner = SimulationRunner(cfg)
        result = runner.run()
        # After step 5, narrative should be active
        assert result.steps[6].active_narratives > 0

    def test_result_as_dict(self, minimal_config):
        """Result.as_dict() should be serializable"""
        runner = SimulationRunner(minimal_config)
        result = runner.run()
        d = result.as_dict()
        assert "config" in d
        assert "summary" in d
        assert "steps" in d
        # Should be JSON serializable
        json_str = json.dumps(d)
        assert len(json_str) > 0

    def test_save_results(self, minimal_config, tmp_path):
        """save_results() should write JSON file"""
        runner = SimulationRunner(minimal_config)
        runner.run()
        output_path = str(tmp_path / "test_result.json")
        runner.save_results(output_path)
        assert os.path.exists(output_path)
        with open(output_path, 'r') as f:
            data = json.load(f)
        assert "summary" in data

    def test_save_results_no_run(self, tmp_path):
        """save_results() before run() should be no-op"""
        cfg = SimulationConfig(quiet=True)
        runner = SimulationRunner(cfg)
        output_path = str(tmp_path / "test_result.json")
        runner.save_results(output_path)
        assert not os.path.exists(output_path)

    def test_result_summary_fields(self, minimal_config):
        """Result summary should have expected fields"""
        runner = SimulationRunner(minimal_config)
        result = runner.run()
        assert result.final_price > 0
        assert result.max_bubble_risk >= 0
        assert result.max_panic_risk >= 0
        assert result.peak_price >= result.trough_price
        assert isinstance(result.regime_distribution, dict)

    def test_step_result_as_dict(self, minimal_config):
        """SimulationStepResult.as_dict() should work"""
        runner = SimulationRunner(minimal_config)
        result = runner.run()
        step_dict = result.steps[0].as_dict()
        assert "step" in step_dict
        assert "price" in step_dict
        assert "regime" in step_dict

    def test_seed_reproducibility(self):
        """Same seed should produce same results"""
        cfg1 = SimulationConfig(n_steps=10, n_retail=3, n_trend=1, n_value=1, seed=123, quiet=True)
        cfg2 = SimulationConfig(n_steps=10, n_retail=3, n_trend=1, n_value=1, seed=123, quiet=True)

        r1 = SimulationRunner(cfg1).run()
        r2 = SimulationRunner(cfg2).run()

        for s1, s2 in zip(r1.steps, r2.steps):
            assert abs(s1.price - s2.price) < 1e-10

    def test_price_bounded(self, small_config):
        """Price should not go negative"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        for step in result.steps:
            assert step.price > 0

    def test_belief_bounded(self, small_config):
        """Mean belief should be in [-1, 1]"""
        runner = SimulationRunner(small_config)
        result = runner.run()
        for step in result.steps:
            assert -1.0 <= step.mean_belief <= 1.0
