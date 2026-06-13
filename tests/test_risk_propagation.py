"""
test_risk_propagation.py
========================
Tests for the Risk Propagation Engine (core/risk_propagation.py)
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.risk_propagation import (
    RiskPropagationEngine, RiskNode, RiskSource, RiskLevel,
    PropagationEvent, CascadeEvent, RiskPropagationReport,
)


# ── RiskNode Tests ──────────────────────────────────────────────

class TestRiskNode:
    def test_creation(self):
        """Should create RiskNode with defaults"""
        node = RiskNode(node_id="test_001")
        assert node.node_id == "test_001"
        assert node.risk_level == 0.0
        assert node.susceptibility == 0.5
        assert node.is_infected is False

    def test_risk_category_safe(self):
        """Low risk should be SAFE"""
        node = RiskNode(node_id="test", risk_level=0.1)
        assert node.risk_category == RiskLevel.SAFE

    def test_risk_category_low(self):
        """Risk 0.2-0.4 should be LOW"""
        node = RiskNode(node_id="test", risk_level=0.3)
        assert node.risk_category == RiskLevel.LOW

    def test_risk_category_moderate(self):
        """Risk 0.4-0.6 should be MODERATE"""
        node = RiskNode(node_id="test", risk_level=0.5)
        assert node.risk_category == RiskLevel.MODERATE

    def test_risk_category_high(self):
        """Risk 0.6-0.8 should be HIGH"""
        node = RiskNode(node_id="test", risk_level=0.7)
        assert node.risk_category == RiskLevel.HIGH

    def test_risk_category_critical(self):
        """Risk >= 0.8 should be CRITICAL"""
        node = RiskNode(node_id="test", risk_level=0.9)
        assert node.risk_category == RiskLevel.CRITICAL


# ── RiskPropagationEngine Tests ────────────────────────────────

class TestRiskPropagationEngine:
    def test_creation(self):
        """Should create engine with default params"""
        engine = RiskPropagationEngine()
        assert engine.contagion_rate == 0.3
        assert engine.node_count == 0

    def test_custom_params(self):
        """Should accept custom parameters"""
        engine = RiskPropagationEngine(
            contagion_rate=0.5,
            amplification_factor=2.0,
            cascade_threshold=0.8,
        )
        assert engine.contagion_rate == 0.5

    def test_build_from_kol_network(self):
        """Should build network from KOL network"""
        engine = RiskPropagationEngine()
        mock_network = MagicMock()
        mock_node1 = MagicMock()
        mock_node1.node_id = "kol_1"
        mock_node1.susceptibility = 0.5
        mock_node1.followers = ["retail_1"]
        mock_node1.following = []
        mock_node2 = MagicMock()
        mock_node2.node_id = "kol_2"
        mock_node2.susceptibility = 0.3
        mock_node2.followers = []
        mock_node2.following = ["kol_1"]
        mock_network.nodes = [mock_node1, mock_node2]
        mock_network.get_kols.return_value = [mock_node1, mock_node2]
        mock_network.get_node.side_effect = lambda x: mock_node1 if x == "kol_1" else mock_node2

        engine.build_from_kol_network(mock_network, agents=[])
        assert engine.node_count == 2

    def test_inject_risk(self):
        """Should inject risk into a node"""
        engine = RiskPropagationEngine()
        mock_network = MagicMock()
        mock_node = MagicMock()
        mock_node.node_id = "node_1"
        mock_node.susceptibility = 0.5
        mock_node.followers = []
        mock_node.following = []
        mock_network.nodes = [mock_node]
        mock_network.get_kols.return_value = [mock_node]

        engine.build_from_kol_network(mock_network, agents=[])
        engine.inject_risk("node_1", 0.8, RiskSource.PRICE_CRASH, step=0)

        assert engine.get_node_risk("node_1") == 0.8

    def test_inject_risk_nonexistent_node(self):
        """Injecting risk into nonexistent node should be no-op"""
        engine = RiskPropagationEngine()
        engine.inject_risk("nonexistent", 0.8, RiskSource.PRICE_CRASH)
        assert engine.get_node_risk("nonexistent") == 0.0

    def test_propagate_with_no_risk(self):
        """Propagation with no risk should yield zero system risk"""
        engine = RiskPropagationEngine()
        mock_network = MagicMock()
        mock_node = MagicMock()
        mock_node.node_id = "node_1"
        mock_node.susceptibility = 0.5
        mock_node.followers = []
        mock_node.following = []
        mock_network.nodes = [mock_node]
        mock_network.get_kols.return_value = [mock_node]

        engine.build_from_kol_network(mock_network, agents=[])
        report = engine.propagate(step=0)
        assert report.system_risk == 0.0

    def test_propagate_with_injected_risk(self):
        """Propagation should spread risk"""
        engine = RiskPropagationEngine()
        mock_network = MagicMock()

        # Create connected nodes
        node1 = MagicMock()
        node1.node_id = "source"
        node1.susceptibility = 0.5
        node1.followers = ["target"]
        node1.following = []

        node2 = MagicMock()
        node2.node_id = "target"
        node2.susceptibility = 0.8
        node2.followers = []
        node2.following = ["source"]

        mock_network.nodes = [node1, node2]
        mock_network.get_kols.return_value = [node1, node2]
        mock_network.get_node.side_effect = lambda x: node1 if x == "source" else node2

        engine.build_from_kol_network(mock_network, agents=[])
        engine.inject_risk("source", 0.8, RiskSource.PRICE_CRASH, step=0)

        report = engine.propagate(step=1)
        # Target should have received some risk
        assert engine.get_node_risk("target") > 0.0

    def test_propagate_returns_report(self):
        """propagate() should return RiskPropagationReport"""
        engine = RiskPropagationEngine()
        engine._nodes["test"] = RiskNode(node_id="test", risk_level=0.5)
        report = engine.propagate(step=0)
        assert isinstance(report, RiskPropagationReport)
        assert report.step == 0

    def test_emotion_amplifies_risk(self):
        """Fear should amplify risk propagation"""
        engine = RiskPropagationEngine()

        # Create two connected nodes
        engine._nodes["a"] = RiskNode(
            node_id="a", risk_level=0.5,
            connections=["b"], susceptibility=0.5,
        )
        engine._nodes["b"] = RiskNode(
            node_id="b", risk_level=0.1,
            connections=["a"], susceptibility=0.8,
        )

        # Propagate without emotion
        report_calm = engine.propagate(step=0)
        risk_after_calm = engine.get_node_risk("b")

        # Reset and propagate with high fear
        engine._nodes["a"].risk_level = 0.5
        engine._nodes["b"].risk_level = 0.1
        mock_emotion = MagicMock()
        mock_emotion.fear = 0.9
        mock_emotion.uncertainty = 0.8
        report_fear = engine.propagate(step=1, emotion=mock_emotion)
        risk_after_fear = engine.get_node_risk("b")

        # Fear should amplify risk propagation
        assert risk_after_fear >= risk_after_calm

    def test_risk_decays_over_time(self):
        """Risk should naturally decay"""
        engine = RiskPropagationEngine()
        engine._nodes["test"] = RiskNode(
            node_id="test", risk_level=0.5,
            recovery_rate=0.1,
        )

        engine.propagate(step=0)
        risk_0 = engine.get_node_risk("test")

        engine.propagate(step=1)
        risk_1 = engine.get_node_risk("test")

        assert risk_1 < risk_0

    def test_high_risk_nodes(self):
        """get_high_risk_nodes() should filter correctly"""
        engine = RiskPropagationEngine()
        engine._nodes["low"] = RiskNode(node_id="low", risk_level=0.1)
        engine._nodes["high"] = RiskNode(node_id="high", risk_level=0.8)

        high_nodes = engine.get_high_risk_nodes(threshold=0.5)
        assert len(high_nodes) == 1
        assert high_nodes[0].node_id == "high"

    def test_history_tracking(self):
        """Should track propagation history"""
        engine = RiskPropagationEngine()
        engine._nodes["test"] = RiskNode(node_id="test", risk_level=0.3)
        engine.propagate(step=0)
        engine.propagate(step=1)
        assert len(engine.history) == 2

    def test_summary(self):
        """summary() should return expected keys"""
        engine = RiskPropagationEngine()
        engine._nodes["test"] = RiskNode(node_id="test", risk_level=0.3)
        engine.propagate(step=0)
        summary = engine.summary()
        assert "steps" in summary
        assert "nodes" in summary
        assert "system_risk" in summary

    def test_price_crash_amplifies_risk(self):
        """Price crash should amplify risk propagation"""
        engine = RiskPropagationEngine()
        engine._nodes["a"] = RiskNode(
            node_id="a", risk_level=0.5,
            connections=["b"], susceptibility=0.5,
        )
        engine._nodes["b"] = RiskNode(
            node_id="b", risk_level=0.3,
            connections=["a"], susceptibility=0.8,
        )

        # Normal propagation
        engine.propagate(step=0, price_change_pct=0.0)
        risk_normal = engine.get_node_risk("b")

        # Reset
        engine._nodes["a"].risk_level = 0.5
        engine._nodes["b"].risk_level = 0.3

        # Crash propagation
        engine.propagate(step=1, price_change_pct=-0.05)
        risk_crash = engine.get_node_risk("b")

        assert risk_crash >= risk_normal

    def test_report_as_dict(self):
        """RiskPropagationReport.as_dict() should be serializable"""
        engine = RiskPropagationEngine()
        engine._nodes["test"] = RiskNode(node_id="test", risk_level=0.5)
        report = engine.propagate(step=0)
        d = report.as_dict()
        assert "step" in d
        assert "system_risk" in d
        assert "risk_distribution" in d
