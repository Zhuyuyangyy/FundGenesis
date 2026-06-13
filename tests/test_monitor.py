"""
test_monitor.py - Reflexivity Monitor Tests
============================================
Comprehensive tests for the reflexivity monitoring system.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.reflexivity_monitor import (
    ReflexivityMonitor, ReflexivityMetrics, MarketRegime,
)


# ── ReflexivityMetrics Tests ───────────────────────────────────

class TestReflexivityMetrics:
    def test_creation(self):
        metrics = ReflexivityMetrics(step=10)
        assert metrics.step == 10
        assert metrics.regime == MarketRegime.NORMAL

    def test_as_dict(self):
        metrics = ReflexivityMetrics(
            step=5,
            reflexivity_index=0.5,
            bubble_risk_score=0.3,
            regime=MarketRegime.NORMAL,
        )
        d = metrics.as_dict()
        assert d["step"] == 5
        assert d["reflexivity_index"] == 0.5
        assert d["regime"] == "normal"


# ── MarketRegime Tests ─────────────────────────────────────────

class TestMarketRegime:
    def test_all_regimes(self):
        assert MarketRegime.NORMAL.value == "normal"
        assert MarketRegime.BUBBLE_FORMING.value == "bubble_forming"
        assert MarketRegime.BUBBLE_PEAK.value == "bubble_peak"
        assert MarketRegime.CRASH.value == "crash"
        assert MarketRegime.PANIC_SPREAD.value == "panic_spread"
        assert MarketRegime.RECOVERY.value == "recovery"


# ── ReflexivityMonitor Tests ───────────────────────────────────

class TestReflexivityMonitor:
    def test_creation(self):
        monitor = ReflexivityMonitor()
        assert len(monitor.history) == 0

    def test_observe_basic(self, market, emotion):
        monitor = ReflexivityMonitor()
        metrics = monitor.observe(
            step=0,
            market=market,
            emotion=emotion,
            kol_network=None,
            narrative_engine=None,
            agents=[],
        )
        assert isinstance(metrics, ReflexivityMetrics)
        assert metrics.step == 0
        assert 0.0 <= metrics.reflexivity_index <= 1.0

    def test_observe_with_agents(self, market, emotion):
        monitor = ReflexivityMonitor()
        agents = [MagicMock(belief=0.5) for _ in range(10)]
        metrics = monitor.observe(
            step=0,
            market=market,
            emotion=emotion,
            kol_network=None,
            narrative_engine=None,
            agents=agents,
        )
        assert metrics.belief_concentration >= 0

    def test_observe_with_kol_network(self, market, emotion, kol_network):
        monitor = ReflexivityMonitor()
        metrics = monitor.observe(
            step=0,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=None,
            agents=[],
        )
        assert metrics.belief_concentration >= 0

    def test_observe_with_narrative_engine(self, market, emotion, narrative_engine):
        monitor = ReflexivityMonitor()
        from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
        narrative_engine.inject(NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
        ))
        metrics = monitor.observe(
            step=0,
            market=market,
            emotion=emotion,
            kol_network=None,
            narrative_engine=narrative_engine,
            agents=[MagicMock()],
        )
        assert metrics.narrative_strength >= 0

    def test_history_tracking(self, market, emotion):
        monitor = ReflexivityMonitor()
        for i in range(5):
            monitor.observe(
                step=i,
                market=market,
                emotion=emotion,
                kol_network=None,
                narrative_engine=None,
                agents=[],
            )
        assert len(monitor.history) == 5

    def test_latest(self, market, emotion):
        monitor = ReflexivityMonitor()
        assert monitor.latest() is None
        monitor.observe(step=0, market=market, emotion=emotion,
                       kol_network=None, narrative_engine=None, agents=[])
        assert monitor.latest() is not None

    def test_regime_summary(self, market, emotion):
        monitor = ReflexivityMonitor()
        for i in range(10):
            monitor.observe(step=i, market=market, emotion=emotion,
                           kol_network=None, narrative_engine=None, agents=[])
        summary = monitor.regime_summary()
        assert "normal" in summary

    def test_critical_steps(self, market, emotion):
        monitor = ReflexivityMonitor()
        for i in range(5):
            monitor.observe(step=i, market=market, emotion=emotion,
                           kol_network=None, narrative_engine=None, agents=[])
        critical = monitor.critical_steps(threshold=0.7)
        assert isinstance(critical, list)

    def test_bubble_risk_bounded(self, market, emotion):
        monitor = ReflexivityMonitor()
        metrics = monitor.observe(
            step=0,
            market=market,
            emotion=emotion,
            kol_network=None,
            narrative_engine=None,
            agents=[],
        )
        assert 0.0 <= metrics.bubble_risk_score <= 1.0
        assert 0.0 <= metrics.panic_risk_score <= 1.0
