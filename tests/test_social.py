"""
test_social.py - Social Network Tests
======================================
Comprehensive tests for KOL network and propagation.
"""

import pytest
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from social.kol_network import KOLNetwork, KOLNode, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity


# ── KOLNetwork Tests ──────────────────────────────────────────

class TestKOLNetwork:
    def test_creation(self):
        network = KOLNetwork()
        assert len(network.nodes) == 0

    def test_add_node(self):
        network = KOLNetwork()
        node = KOLNode(node_id="test_1", tier=KOLTier.MACRO, name="Test")
        network.add_node(node)
        assert len(network.nodes) == 1
        assert network.get_node("test_1") is not None

    def test_connect(self):
        network = KOLNetwork()
        n1 = KOLNode(node_id="a", tier=KOLTier.MACRO)
        n2 = KOLNode(node_id="b", tier=KOLTier.RETAIL)
        network.add_node(n1)
        network.add_node(n2)
        network.connect("b", "a")
        assert "a" in network.get_node("b").following
        assert "b" in network.get_node("a").followers

    def test_get_kols(self):
        network = KOLNetwork()
        network.add_node(KOLNode(node_id="k1", tier=KOLTier.MACRO))
        network.add_node(KOLNode(node_id="r1", tier=KOLTier.RETAIL))
        kols = network.get_kols()
        assert len(kols) == 1
        assert kols[0].node_id == "k1"

    def test_get_retail(self):
        network = KOLNetwork()
        network.add_node(KOLNode(node_id="k1", tier=KOLTier.MACRO))
        network.add_node(KOLNode(node_id="r1", tier=KOLTier.RETAIL))
        retail = network.get_retail()
        assert len(retail) == 1
        assert retail[0].node_id == "r1"

    def test_belief_statistics(self):
        network = KOLNetwork()
        network.add_node(KOLNode(node_id="n1", tier=KOLTier.RETAIL, belief_state=0.5))
        network.add_node(KOLNode(node_id="n2", tier=KOLTier.RETAIL, belief_state=-0.3))
        stats = network.belief_statistics()
        assert "mean_belief" in stats
        assert "belief_concentration" in stats
        assert stats["retail_count"] == 2

    def test_build_default_network(self):
        network = KOLNetwork()
        network.build_default_network(n_macro=2, n_influencer=3, n_micro=5, n_retail=20)
        assert len(network.nodes) == 30
        assert len(network.get_kols()) == 10  # macro + influencer + micro
        assert len(network.get_retail()) == 20

    def test_reset_exposure_all(self):
        network = KOLNetwork()
        node = KOLNode(node_id="n1", tier=KOLTier.RETAIL, narrative_exposure=0.8)
        network.add_node(node)
        network.reset_exposure_all(decay=0.5)
        assert network.get_node("n1").narrative_exposure == pytest.approx(0.4)


class TestKOLNode:
    def test_creation(self):
        node = KOLNode(
            node_id="test",
            tier=KOLTier.MACRO,
            name="TestKOL",
            influence_score=0.8,
            trust_level=0.7,
        )
        assert node.node_id == "test"
        assert node.is_kol is True

    def test_is_kol_property(self):
        macro = KOLNode(tier=KOLTier.MACRO)
        retail = KOLNode(tier=KOLTier.RETAIL)
        assert macro.is_kol is True
        assert retail.is_kol is False

    def test_receive_exposure(self):
        node = KOLNode(tier=KOLTier.RETAIL, susceptibility=0.5)
        node.receive_exposure(0.5)
        assert node.narrative_exposure > 0

    def test_receive_exposure_with_confirmation_bias(self):
        node = KOLNode(
            tier=KOLTier.RETAIL,
            susceptibility=0.8,
            confirmation_bias=0.5,
            belief_state=0.3,
        )
        initial_belief = node.belief_state
        node.receive_exposure(0.5)
        assert node.belief_state >= initial_belief  # Should reinforce positive belief

    def test_reset_exposure(self):
        node = KOLNode(tier=KOLTier.RETAIL, narrative_exposure=0.8)
        node.reset_exposure(decay=0.5)
        assert node.narrative_exposure == pytest.approx(0.4)

    def test_influence_on(self):
        source = KOLNode(
            tier=KOLTier.MACRO,
            influence_score=0.8,
            trust_level=0.7,
        )
        target = KOLNode(
            tier=KOLTier.RETAIL,
            susceptibility=0.6,
            trust_level=0.5,
        )
        influence = source.influence_on(target, narrative_strength=0.7)
        assert influence > 0

    def test_influence_on_inactive_target(self):
        source = KOLNode(tier=KOLTier.MACRO, influence_score=0.8)
        target = KOLNode(tier=KOLTier.RETAIL, is_active=False)
        influence = source.influence_on(target, narrative_strength=0.7)
        assert influence == 0.0


# ── PropagationModel Tests ─────────────────────────────────────

class TestPropagationModel:
    def test_creation(self, kol_network):
        model = PropagationModel(kol_network)
        assert len(model.active_narratives) == 0

    def test_inject_narrative(self, kol_network):
        model = PropagationModel(kol_network)
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
            duration=10,
        )
        model.inject_narrative(event)
        assert len(model.active_narratives) == 1

    def test_step_propagates(self, kol_network):
        model = PropagationModel(kol_network)
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.8,
            duration=10,
        )
        model.inject_narrative(event)
        strengths = model.step()
        assert len(strengths) == 1

    def test_narrative_expires(self, kol_network):
        model = PropagationModel(kol_network)
        event = NarrativeEvent(
            name="Short",
            category=NarrativeCategory.POLICY,
            polarity=Polarity.NEGATIVE,
            intensity=0.5,
            duration=2,
        )
        model.inject_narrative(event)
        model.step()
        model.step()
        model.step()  # Should expire
        assert len(model.active_narratives) == 0

    def test_get_node_exposure(self, kol_network):
        model = PropagationModel(kol_network)
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
            duration=10,
        )
        model.inject_narrative(event)
        model.step()
        exposures = model.get_node_exposure(event._id)
        assert len(exposures) > 0

    def test_get_network_exposure(self, kol_network):
        model = PropagationModel(kol_network)
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
            duration=10,
        )
        model.inject_narrative(event)
        model.step()
        total = model.get_network_exposure(event._id)
        assert total >= 0

    def test_get_tier_exposure(self, kol_network):
        model = PropagationModel(kol_network)
        event = NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
            intensity=0.7,
            duration=10,
        )
        model.inject_narrative(event)
        model.step()
        tier_exp = model.get_tier_exposure(event._id)
        assert "macro" in tier_exp

    def test_summary(self, kol_network):
        model = PropagationModel(kol_network)
        model.inject_narrative(NarrativeEvent(
            name="Test",
            category=NarrativeCategory.FINTECH,
            polarity=Polarity.POSITIVE,
        ))
        summary = model.summary()
        assert "active_count" in summary
        assert summary["active_count"] == 1
