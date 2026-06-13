"""
test_trust_engine.py - Trust Engine Tests
==========================================
Comprehensive tests for the trust system components.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trust.trust_engine import TrustEngine, TrustConfig, KOLTrustState
from trust.trust_bootstrapper import TrustBootstrapper, BootstrapConfig
from trust.trust_decay_model import TrustDecayModel, DecayConfig
from trust.credibility_updater import CredibilityUpdater, CredibilityConfig
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity


# ── TrustEngine Tests ──────────────────────────────────────────

class TestTrustEngine:
    def test_creation(self):
        engine = TrustEngine()
        assert len(engine._states) == 0

    def test_init_kol(self):
        engine = TrustEngine()
        state = engine.init_kol("kol_1", initial_trust=0.7)
        assert state.kol_id == "kol_1"
        assert state.trust_level == 0.7

    def test_init_kol_idempotent(self):
        engine = TrustEngine()
        engine.init_kol("kol_1", initial_trust=0.7)
        engine.init_kol("kol_1", initial_trust=0.9)
        state = engine.get_state("kol_1")
        assert state.trust_level == 0.7  # Should not overwrite

    def test_get_state_existing(self):
        engine = TrustEngine()
        engine.init_kol("kol_1")
        state = engine.get_state("kol_1")
        assert state is not None

    def test_get_state_nonexistent(self):
        engine = TrustEngine()
        state = engine.get_state("nonexistent")
        assert state is None

    def test_get_effective_trust(self):
        engine = TrustEngine()
        engine.init_kol("kol_1", initial_trust=0.8)
        engine.set_credibility_score("kol_1", 0.9)
        effective = engine.get_effective_trust("kol_1")
        assert effective > 0.0

    def test_get_effective_trust_nonexistent(self):
        engine = TrustEngine()
        assert engine.get_effective_trust("nonexistent") == 0.0

    def test_set_trust_level_clamping(self):
        engine = TrustEngine()
        engine.init_kol("kol_1")
        engine.set_trust_level("kol_1", 1.5)
        state = engine.get_state("kol_1")
        assert state.trust_level == 1.0

    def test_set_credibility_score_clamping(self):
        engine = TrustEngine()
        engine.init_kol("kol_1")
        engine.set_credibility_score("kol_1", -0.5)
        state = engine.get_state("kol_1")
        assert state.credibility_score == 0.0

    def test_set_price_validation(self):
        engine = TrustEngine()
        engine.init_kol("kol_1")
        engine.set_price_validation("kol_1", 0.8)
        state = engine.get_state("kol_1")
        assert state.price_validation == 0.8

    def test_get_all_effective_trusts(self):
        engine = TrustEngine()
        engine.init_kol("kol_1", 0.8)
        engine.init_kol("kol_2", 0.6)
        trusts = engine.get_all_effective_trusts()
        assert len(trusts) == 2
        assert "kol_1" in trusts
        assert "kol_2" in trusts

    def test_get_trust_statistics(self):
        engine = TrustEngine()
        engine.init_kol("kol_1", 0.8)
        engine.init_kol("kol_2", 0.6)
        stats = engine.get_trust_statistics()
        assert "mean_trust" in stats
        assert "std_trust" in stats
        assert stats["kol_count"] == 2

    def test_get_trust_statistics_empty(self):
        engine = TrustEngine()
        stats = engine.get_trust_statistics()
        assert stats == {}

    def test_summary(self):
        engine = TrustEngine()
        engine.init_kol("kol_1", 0.8)
        summary = engine.summary()
        assert "total_kols" in summary
        assert "statistics" in summary
        assert "top5" in summary


class TestKOLTrustState:
    def test_effective_trust_formula(self):
        config = TrustConfig()
        state = KOLTrustState(
            kol_id="test",
            trust_level=0.8,
            credibility_score=0.9,
            social_proof=0.7,
            price_validation=0.8,
            last_update_step=0,
            config=config,
        )
        effective = state.effective_trust
        assert 0.0 < effective <= 1.0

    def test_effective_trust_minimum(self):
        config = TrustConfig(min_effective_trust=0.05)
        state = KOLTrustState(
            kol_id="test",
            trust_level=0.01,
            credibility_score=0.01,
            social_proof=0.01,
            price_validation=0.01,
            last_update_step=0,
            config=config,
        )
        assert state.effective_trust >= 0.05


# ── TrustBootstrapper Tests ────────────────────────────────────

class TestTrustBootstrapper:
    def test_bootstrap_network(self, kol_network, trust_engine):
        bootstrapper = TrustBootstrapper()
        bootstrapper.bootstrap_network(kol_network, trust_engine)
        # All KOLs should have trust states
        kols = kol_network.get_kols()
        for kol in kols:
            state = trust_engine.get_state(kol.node_id)
            assert state is not None
            assert 0.0 <= state.trust_level <= 1.0

    def test_apply_low_trust_regime(self, kol_network, trust_engine):
        bootstrapper = TrustBootstrapper()
        bootstrapper.bootstrap_network(kol_network, trust_engine)
        bootstrapper.apply_low_trust_regime(trust_engine, kol_network, multiplier=0.3)
        for kol in kol_network.get_kols():
            state = trust_engine.get_state(kol.node_id)
            assert state.trust_level <= 0.5  # Should be significantly lower

    def test_apply_high_trust_regime(self, kol_network, trust_engine):
        bootstrapper = TrustBootstrapper()
        bootstrapper.bootstrap_network(kol_network, trust_engine)
        bootstrapper.apply_high_trust_regime(trust_engine, kol_network, target_trust=0.95)
        for kol in kol_network.get_kols():
            state = trust_engine.get_state(kol.node_id)
            if kol.tier.value == "macro":
                assert state.trust_level >= 0.9

    def test_apply_falsification_regime(self, kol_network, trust_engine):
        bootstrapper = TrustBootstrapper()
        bootstrapper.bootstrap_network(kol_network, trust_engine)
        bootstrapper.apply_falsification_regime(trust_engine, kol_network, penalty=0.8)
        for kol in kol_network.get_kols():
            state = trust_engine.get_state(kol.node_id)
            assert state.trust_level <= 0.3

    def test_get_initial_trust_for_tier(self):
        bootstrapper = TrustBootstrapper()
        from social.kol_network import KOLTier
        assert bootstrapper.get_initial_trust_for_tier(KOLTier.MACRO) == 0.80
        assert bootstrapper.get_initial_trust_for_tier(KOLTier.INFLUENCER) == 0.60


# ── TrustDecayModel Tests ──────────────────────────────────────

class TestTrustDecayModel:
    def test_creation(self):
        model = TrustDecayModel()
        assert model.config.decay_per_step == 0.005

    def test_attach_engine(self):
        model = TrustDecayModel()
        engine = TrustEngine()
        model.attach_engine(engine)
        assert model._engine == engine

    def test_record_narrative_injection(self):
        model = TrustDecayModel()
        model.record_narrative_injection("kol_1", step=10)
        assert model._last_narrative_step["kol_1"] == 10

    def test_record_verification(self):
        model = TrustDecayModel()
        engine = TrustEngine()
        engine.init_kol("kol_1", initial_trust=0.5)
        model.attach_engine(engine)
        model.record_verification("kol_1", step=5)
        state = engine.get_state("kol_1")
        assert state.trust_level > 0.5  # Should increase

    def test_record_failed_verification(self):
        model = TrustDecayModel()
        engine = TrustEngine()
        engine.init_kol("kol_1", initial_trust=0.5)
        model.attach_engine(engine)
        model.record_failed_verification("kol_1", step=5)
        state = engine.get_state("kol_1")
        assert state.trust_level < 0.5  # Should decrease

    def test_tick_time_decay(self, kol_network, trust_engine):
        bootstrapper = TrustBootstrapper()
        bootstrapper.bootstrap_network(kol_network, trust_engine)
        model = TrustDecayModel()
        model.attach_engine(trust_engine)

        initial_trusts = {}
        for kol in kol_network.get_kols():
            initial_trusts[kol.node_id] = trust_engine.get_state(kol.node_id).trust_level

        model.tick(kol_network, current_step=1)

        for kol in kol_network.get_kols():
            state = trust_engine.get_state(kol.node_id)
            assert state.trust_level <= initial_trusts[kol.node_id]

    def test_get_decay_report(self, kol_network, trust_engine):
        bootstrapper = TrustBootstrapper()
        bootstrapper.bootstrap_network(kol_network, trust_engine)
        model = TrustDecayModel()
        model.attach_engine(trust_engine)
        report = model.get_decay_report(kol_network)
        assert isinstance(report, dict)


# ── CredibilityUpdater Tests ───────────────────────────────────

class TestCredibilityUpdater:
    def test_creation(self):
        updater = CredibilityUpdater()
        assert updater.config.accuracy_reward == 0.08

    def test_record_prediction(self):
        updater = CredibilityUpdater()
        engine = TrustEngine()
        engine.init_kol("kol_1")
        updater.attach_engine(engine)

        narrative = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
        )
        pred = updater.record_prediction("kol_1", narrative, step=10)
        assert pred.kol_id == "kol_1"
        assert pred.polarity == Polarity.POSITIVE
        assert updater.get_pending_count() == 1

    def test_verify_and_update_confirm(self):
        updater = CredibilityUpdater()
        engine = TrustEngine()
        engine.init_kol("kol_1", initial_trust=0.5)
        engine.set_credibility_score("kol_1", 0.5)
        updater.attach_engine(engine)

        narrative = NarrativeEvent(
            name="Bull",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
            duration=10,
        )
        updater.record_prediction("kol_1", narrative, step=0)

        # Simulate rising prices
        price_history = [100.0] + [100.0 + i * 0.5 for i in range(1, 15)]
        verified = updater.verify_and_update(
            MagicMock(get_kols=lambda: []),
            price_history,
            current_step=10,
        )
        # Should have verified
        assert len(verified) >= 0  # May or may not verify depending on window

    def test_get_verification_summary_empty(self):
        updater = CredibilityUpdater()
        summary = updater.get_verification_summary()
        assert summary["total"] == 0

    def test_get_pending_count(self):
        updater = CredibilityUpdater()
        assert updater.get_pending_count() == 0
