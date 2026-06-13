"""
test_narrative.py - Narrative Engine Tests
==========================================
Comprehensive tests for the narrative system.
"""

import pytest
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from narrative.narrative_event import (
    NarrativeEvent, NarrativeRegistry, NarrativeCategory, Polarity
)
from narrative.narrative_engine import NarrativeEngine, NarrativeEngineConfig
from core.emotion_field import EmotionField


# ── NarrativeEvent Tests ───────────────────────────────────────

class TestNarrativeEvent:
    def test_creation(self):
        event = NarrativeEvent(
            name="Test Event",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
            credibility=0.8,
        )
        assert event.name == "Test Event"
        assert event.category == NarrativeCategory.FINTECH
        assert event.polarity == Polarity.POSITIVE
        assert event.intensity == 0.7
        assert event.credibility == 0.8

    def test_tick_decrements_remaining(self):
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.POLICY,
            polarity=Polarity.NEGATIVE,
            duration=5,
        )
        assert event.is_active is True
        for _ in range(5):
            event.tick()
        assert event.is_active is False

    def test_remaining_ratio(self):
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.POLICY,
            polarity=Polarity.NEUTRAL,
            duration=10,
        )
        assert event.remaining_ratio == 1.0
        for _ in range(5):
            event.tick()
        assert event.remaining_ratio == pytest.approx(0.5)

    def test_effective_intensity(self):
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.POLICY,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
            duration=10,
        )
        assert event.effective_intensity == pytest.approx(0.8)
        for _ in range(5):
            event.tick()
        assert event.effective_intensity == pytest.approx(0.4)

    def test_to_impact_positive(self):
        event = NarrativeEvent(
            name="Bull",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
            credibility=0.7,
            novelty=0.5,
        )
        impact = event.to_impact()
        assert impact["greed_delta"] > 0
        assert impact["confidence_delta"] > 0

    def test_to_impact_negative(self):
        event = NarrativeEvent(
            name="Bear",
            category=NarrativeCategory.REGULATORY,
            polarity=Polarity.NEGATIVE,
            intensity=0.8,
            credibility=0.7,
            novelty=0.5,
        )
        impact = event.to_impact()
        assert impact["fear_delta"] > 0
        assert impact["uncertainty_delta"] > 0

    def test_to_impact_neutral(self):
        event = NarrativeEvent(
            name="Meh",
            category=NarrativeCategory.MACRO,
            polarity=Polarity.NEUTRAL,
            intensity=0.5,
        )
        impact = event.to_impact()
        assert impact["uncertainty_delta"] > 0

    def test_unique_ids(self):
        e1 = NarrativeEvent(name="A", category=NarrativeCategory.POLICY, polarity=Polarity.POSITIVE)
        e2 = NarrativeEvent(name="B", category=NarrativeCategory.POLICY, polarity=Polarity.NEGATIVE)
        assert e1._id != e2._id


# ── NarrativeRegistry Tests ────────────────────────────────────

class TestNarrativeRegistry:
    def test_add_and_active(self):
        registry = NarrativeRegistry()
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            duration=5,
        )
        registry.add(event)
        assert len(registry) == 1
        assert len(registry.active) == 1

    def test_tick_all_removes_expired(self):
        registry = NarrativeRegistry()
        event = NarrativeEvent(
            name="Short",
            category=NarrativeCategory.POLICY,
            polarity=Polarity.NEGATIVE,
            duration=2,
        )
        registry.add(event)
        registry.tick_all()
        registry.tick_all()
        expired = registry.tick_all()
        assert len(registry.active) == 0

    def test_active_by_category(self):
        registry = NarrativeRegistry()
        registry.add(NarrativeEvent(
            name="Policy",
            category=NarrativeCategory.POLICY,
            polarity=Polarity.POSITIVE,
        ))
        registry.add(NarrativeEvent(
            name="Fintech",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.NEGATIVE,
        ))
        policy = registry.active_by_category(NarrativeCategory.POLICY)
        assert len(policy) == 1
        assert policy[0].name == "Policy"

    def test_aggregate_impact(self):
        registry = NarrativeRegistry()
        registry.add(NarrativeEvent(
            name="Bull1",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
        ))
        registry.add(NarrativeEvent(
            name="Bull2",
            category=NarrativeCategory.EARNINGS,
            polarity=Polarity.POSITIVE,
            intensity=0.6,
        ))
        impact = registry.aggregate_impact()
        assert impact["greed_delta"] > 0


# ── NarrativeEngine Tests ──────────────────────────────────────

class TestNarrativeEngine:
    def test_creation(self):
        engine = NarrativeEngine()
        assert len(engine.registry) == 0

    def test_inject(self):
        engine = NarrativeEngine()
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
        )
        engine.inject(event)
        assert len(engine.registry) == 1

    def test_compute_belief_shift(self):
        engine = NarrativeEngine()
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
            credibility=0.7,
            novelty=0.5,
            duration=10,
        )
        engine.inject(event)
        shift = engine.compute_belief_shift(event._id)
        assert shift >= 0  # Positive narrative should give positive shift

    def test_aggregate_belief_shift(self):
        engine = NarrativeEngine()
        engine.inject(NarrativeEvent(
            name="Bull",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
        ))
        engine.inject(NarrativeEvent(
            name="Bull2",
            category=NarrativeCategory.EARNINGS,
            polarity=Polarity.POSITIVE,
            intensity=0.6,
        ))
        total = engine.aggregate_belief_shift()
        assert total >= 0

    def test_propagate_to_emotion(self):
        engine = NarrativeEngine()
        emotion = EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)
        engine.inject(NarrativeEvent(
            name="Bull",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
        ))
        initial_greed = emotion.greed
        engine.propagate_to_emotion(emotion, price_change_pct=0.02)
        assert emotion.greed >= initial_greed

    def test_narrative_strength(self):
        engine = NarrativeEngine()
        engine.inject(NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
            credibility=0.7,
        ))
        strength = engine.narrative_strength()
        assert strength > 0

    def test_narrative_strength_multiplier(self):
        engine = NarrativeEngine()
        engine.inject(NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
        ))
        full_strength = engine.narrative_strength()
        engine.narrative_strength_multiplier = 0.5
        reduced = engine.narrative_strength()
        assert reduced < full_strength

    def test_get_narrative_penetration(self):
        engine = NarrativeEngine()
        engine.inject(NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
        ))
        pen = engine.get_narrative_penetration(total_agents=100)
        assert 0 <= pen <= 1

    def test_summary(self):
        engine = NarrativeEngine()
        engine.inject(NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
        ))
        summary = engine.summary()
        assert "active_count" in summary
        assert "total_strength" in summary
        assert summary["active_count"] == 1

    def test_tick(self):
        engine = NarrativeEngine()
        event = NarrativeEvent(
            name="Short",
            category=NarrativeCategory.POLICY,
            polarity=Polarity.NEGATIVE,
            duration=2,
        )
        engine.inject(event)
        engine.tick()
        engine.tick()
        expired = engine.tick()
        assert len(engine.registry.active) == 0
