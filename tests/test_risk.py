"""
test_risk.py - Risk Module Tests
=================================
Comprehensive tests for risk detection and regulation.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk.manipulation_risk_agent import (
    ManipulationRiskAgent, RiskLevel, PatternType,
    ManipulationRiskReport, PatternDetection,
)
from risk.regulator_agent import (
    RegulatorAgent, InterventionAction, InterventionIntensity,
    InterventionPolicy, CoolingMechanism, InvestorProtection,
    RegulatorState,
)


# ── ManipulationRiskAgent Tests ────────────────────────────────

class TestManipulationRiskAgent:
    def test_creation(self):
        agent = ManipulationRiskAgent()
        assert agent.action_thresholds["monitor"] == 0.20

    def test_creation_custom_thresholds(self):
        agent = ManipulationRiskAgent(
            action_thresholds={"monitor": 0.15, "human_review": 0.25, "block": 0.60}
        )
        assert agent.action_thresholds["monitor"] == 0.15

    def test_reset(self):
        agent = ManipulationRiskAgent()
        agent._risk_history.append(0.5)
        agent.reset()
        assert len(agent._risk_history) == 0

    def test_risk_level_classification(self):
        agent = ManipulationRiskAgent()
        assert agent._score_to_risk_level(0.1) == RiskLevel.LOW
        assert agent._score_to_risk_level(0.4) == RiskLevel.MEDIUM
        assert agent._score_to_risk_level(0.6) == RiskLevel.HIGH
        assert agent._score_to_risk_level(0.8) == RiskLevel.CRITICAL

    def test_score_to_action(self):
        agent = ManipulationRiskAgent()
        assert agent._score_to_action(0.1) == "allow"
        assert agent._score_to_action(0.3) == "monitor"
        assert agent._score_to_action(0.6) == "human_review"
        assert agent._score_to_action(0.9) == "block"

    def test_record_kol_spread(self):
        agent = ManipulationRiskAgent()
        agent.record_kol_spread(123, "kol_1")
        agent.record_kol_spread(123, "kol_2")
        assert len(agent._kol_spread_map[123]) == 2

    def test_record_price_feedback(self):
        agent = ManipulationRiskAgent()
        agent.record_price_feedback(123, 0.05, 0.7, step=10)
        assert len(agent._injected_price_events) == 1

    def test_record_fomo_signal(self):
        agent = ManipulationRiskAgent()
        agent.record_fomo_signal(0.8, 0.9, 0.7, step=5)
        assert len(agent._injected_fomo_signals) == 1

    def test_record_trust_bootstrap(self):
        agent = ManipulationRiskAgent()
        agent.record_trust_bootstrap("kol_1", 2.0, "test", step=5)
        assert len(agent._injected_trust_events) == 1


class TestManipulationRiskReport:
    def test_as_dict(self):
        report = ManipulationRiskReport(
            step=10,
            manipulation_risk_score=0.5,
            risk_level=RiskLevel.MEDIUM,
            detected_patterns=[],
            recommended_action="monitor",
            confidence=0.7,
            kol_coordination_score=0.3,
            self_validation_score=0.2,
            fomo_score=0.4,
            trust_build_score=0.1,
        )
        d = report.as_dict()
        assert "step" in d
        assert "manipulation_risk_score" in d
        assert d["risk_level"] == "medium"


# ── RegulatorAgent Tests ───────────────────────────────────────

class TestRegulatorAgent:
    def test_creation(self):
        regulator = RegulatorAgent()
        assert regulator.current_intensity == InterventionIntensity.NONE

    def test_reset(self):
        regulator = RegulatorAgent()
        regulator.state.narrative_cap = 0.5
        regulator.reset()
        assert regulator.state.narrative_cap == 1.0

    def test_step_no_risk(self):
        regulator = RegulatorAgent()
        effect = regulator.step(
            risk_score=0.1,
            market_state={"price": 100.0},
        )
        assert effect.step == 1
        # NONE intensity produces no actions
        assert regulator.current_intensity == InterventionIntensity.NONE

    def test_step_light_intervention(self):
        regulator = RegulatorAgent()
        effect = regulator.step(
            risk_score=0.4,
            market_state={"price": 100.0, "bubble_risk": 0.3},
        )
        assert "narrative_throttle" in effect.actions
        assert "risk_warning" in effect.actions

    def test_step_moderate_intervention(self):
        regulator = RegulatorAgent()
        effect = regulator.step(
            risk_score=0.6,
            market_state={"price": 100.0, "bubble_risk": 0.5},
        )
        assert "kol_downweight" in effect.actions

    def test_step_strong_intervention(self):
        regulator = RegulatorAgent()
        effect = regulator.step(
            risk_score=0.8,
            market_state={"price": 100.0, "bubble_risk": 0.7},
        )
        assert "trading_cooldown" in effect.actions

    def test_active_interventions(self):
        regulator = RegulatorAgent()
        regulator.step(risk_score=0.6, market_state={})
        active = regulator.active_interventions
        assert "narrative_throttle" in active

    def test_get_summary(self):
        regulator = RegulatorAgent()
        regulator.step(risk_score=0.1, market_state={})
        summary = regulator.get_summary()
        assert "total_interventions" in summary


class TestInterventionPolicy:
    def test_select_intensity_none(self):
        assert InterventionPolicy.select_intensity(0.1) == InterventionIntensity.NONE

    def test_select_intensity_light(self):
        assert InterventionPolicy.select_intensity(0.4) == InterventionIntensity.LIGHT

    def test_select_intensity_moderate(self):
        assert InterventionPolicy.select_intensity(0.6) == InterventionIntensity.MODERATE

    def test_select_intensity_strong(self):
        assert InterventionPolicy.select_intensity(0.8) == InterventionIntensity.STRONG

    def test_get_actions_none(self):
        actions = InterventionPolicy.get_actions(InterventionIntensity.NONE)
        assert InterventionAction.NO_ACTION in actions

    def test_get_actions_light(self):
        actions = InterventionPolicy.get_actions(InterventionIntensity.LIGHT)
        assert InterventionAction.NARRATIVE_THROTTLE in actions
        assert InterventionAction.RISK_WARNING in actions

    def test_get_actions_strong(self):
        actions = InterventionPolicy.get_actions(InterventionIntensity.STRONG)
        assert InterventionAction.TRADING_COOLDOWN in actions


class TestCoolingMechanism:
    def test_compute_duration(self):
        dur = CoolingMechanism.compute_duration(0.5, InterventionIntensity.LIGHT)
        assert dur >= 0

    def test_compute_duration_strong(self):
        dur = CoolingMechanism.compute_duration(0.5, InterventionIntensity.STRONG)
        assert dur > 0


class TestInvestorProtection:
    def test_issue_warning(self):
        state = RegulatorState()
        InvestorProtection.issue_warning(state, 0.7)
        assert state.warning_active is True
        assert state.warning_strength > 0

    def test_decay_warning(self):
        state = RegulatorState()
        InvestorProtection.issue_warning(state, 0.7)
        for _ in range(10):
            InvestorProtection.decay_warning(state)
        assert state.warning_active is False
