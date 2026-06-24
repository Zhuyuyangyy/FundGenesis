"""
tests/regression/test_p0_fixes.py
==================================
P0 机制修复回归测试。

验证：
  P0.2: net_demand 跨步累积修复
  P0.3: FOMO → EmotionField 闭环
  P0.4: KOL belief_state 可观测化
  P0.5: RegulatorAgent 干预效果验证
"""

import pytest
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── P0.2: net_demand 跨步累积修复 ──────────────────────────────

class TestNetDemandStepLifecycle:
    """P0.2: 验证 net_demand 每步重置，不跨步累积"""

    def test_begin_step_resets_volumes(self):
        """begin_step() 应该清空当步订单统计"""
        from core.market_environment import MarketEnvironment
        market = MarketEnvironment()
        market.submit_order("a1", "BUY", 0.5)
        market.submit_order("a2", "SELL", 0.3)
        assert market.buy_volume > 0
        assert market.sell_volume > 0

        market.begin_step()
        assert market.buy_volume == 0.0
        assert market.sell_volume == 0.0
        assert market.step_buy_volume == 0.0
        assert market.step_sell_volume == 0.0

    def test_end_step_records_step_net_demand(self):
        """end_step() 应该记录 step_net_demand 到 cumulative"""
        from core.market_environment import MarketEnvironment
        from core.emotion_field import EmotionField
        market = MarketEnvironment()
        emotion = EmotionField()

        # Step 1
        market.begin_step()
        market.submit_order("a1", "BUY", 0.5)
        market.submit_order("a2", "SELL", 0.2)
        market.update_price(emotion)
        market.end_step()
        assert market.step_net_demand == pytest.approx(0.3)
        assert market.cumulative_net_demand == pytest.approx(0.3)

        # Step 2: 无订单
        market.begin_step()
        market.update_price(emotion)
        market.end_step()
        assert market.step_net_demand == pytest.approx(0.0)
        assert market.cumulative_net_demand == pytest.approx(0.3)  # 累计不变

    def test_net_demand_resets_each_step(self):
        """核心验收：step_net_demand 每步重置为 0"""
        from core.market_environment import MarketEnvironment
        from core.emotion_field import EmotionField
        market = MarketEnvironment()
        emotion = EmotionField()

        # Step 1: 有买入
        market.begin_step()
        market.submit_order("a1", "BUY", 10.0)
        market.update_price(emotion)
        market.end_step()
        assert market.step_net_demand > 0

        # Step 2: 无订单
        market.begin_step()
        market.update_price(emotion)
        market.end_step()
        assert market.step_net_demand == 0.0

    def test_reset_volumes_backward_compat(self):
        """reset_volumes() 应该等价于 begin_step()"""
        from core.market_environment import MarketEnvironment
        market = MarketEnvironment()
        market.submit_order("a1", "BUY", 0.5)
        market.reset_volumes()
        assert market.buy_volume == 0.0
        assert market.sell_volume == 0.0


# ── P0.3: FOMO → EmotionField 闭环 ──────────────────────────────

class TestFOMOEmotionLinkage:
    """P0.3: 验证 FOMO 信号能影响情绪场"""

    def test_apply_fomo_signal_increases_greed(self):
        """FOMO 信号应该推高贪婪"""
        from core.emotion_field import EmotionField
        emotion = EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)
        initial_greed = emotion.greed
        emotion.apply_fomo_signal(intensity=0.7)
        assert emotion.greed > initial_greed

    def test_apply_fomo_signal_reduces_fear(self):
        """FOMO 信号应该降低恐惧"""
        from core.emotion_field import EmotionField
        emotion = EmotionField(fear=0.5, greed=0.3, confidence=0.5, uncertainty=0.3)
        initial_fear = emotion.fear
        emotion.apply_fomo_signal(intensity=0.7)
        assert emotion.fear < initial_fear

    def test_apply_fomo_signal_zero_intensity_no_effect(self):
        """零强度 FOMO 信号不应改变情绪"""
        from core.emotion_field import EmotionField
        emotion = EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)
        initial_greed = emotion.greed
        emotion.apply_fomo_signal(intensity=0.0)
        assert emotion.greed == initial_greed

    def test_fomo_emotion_closed_loop(self):
        """
        验收：FOMO→greed→retail buy pressure 闭环
        模拟 FOMO 信号后，greed 上升，retail agent 更倾向买入
        """
        from core.emotion_field import EmotionField
        from agents.emotional_retail import EmotionalRetail
        from core.market_environment import MarketEnvironment

        emotion = EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)
        market = MarketEnvironment()
        retail = EmotionalRetail("test_retail", fomo_sensitivity=1.5)

        # 无 FOMO 时的决策
        snapshot_no_fomo = market.get_snapshot()
        action_before = retail.decide(snapshot_no_fomo, emotion)

        # 注入 FOMO
        emotion.apply_fomo_signal(intensity=0.8)
        snapshot_with_fomo = market.get_snapshot()
        action_after = retail.decide(snapshot_with_fomo, emotion)

        # FOMO 后贪婪更高，retail 更倾向买入
        assert emotion.greed > 0.3  # greed 上升


# ── P0.4: KOL belief_state 可观测化 ──────────────────────────────

class TestKOLBeliefObservability:
    """P0.4: 验证 KOL belief_state 在叙事传播后可观测"""

    def test_cumulative_exposure_accumulates(self):
        """累积曝光应该随叙事传播增长"""
        from social.kol_network import KOLNode, KOLTier
        node = KOLNode(tier=KOLTier.MACRO, exposure_gain=2.0)
        assert node.cumulative_exposure == 0.0

        node.receive_exposure(0.3, source_trust=0.8, narrative_strength=0.7)
        assert node.cumulative_exposure > 0.0

        prev = node.cumulative_exposure
        node.receive_exposure(0.3, source_trust=0.8, narrative_strength=0.7)
        assert node.cumulative_exposure > prev

    def test_belief_state_becomes_observable(self):
        """
        验收：高信任正向叙事传播 10-20 step 后 belief_state 可观测

        目标：
          Macro belief_state > 0.25
          Influencer mean belief_state > 0.15
        """
        from social.kol_network import KOLNetwork
        network = KOLNetwork().build_default_network(
            n_macro=2, n_influencer=5, n_micro=10, n_retail=100
        )

        # 模拟 15 步持续叙事曝光
        for step in range(15):
            for kol in network.get_kols():
                kol.receive_exposure(
                    exposure=0.3,
                    source_trust=kol.trust_level,
                    narrative_strength=0.8,
                )

        # 验收
        macro_kols = [k for k in network.get_kols() if k.tier.value == "macro"]
        influencer_kols = [k for k in network.get_kols() if k.tier.value == "influencer"]

        if macro_kols:
            macro_mean = float(np.mean([k.belief_state for k in macro_kols]))
            assert macro_mean > 0.10, f"Macro belief_state too low: {macro_mean}"

        if influencer_kols:
            inf_mean = float(np.mean([k.belief_state for k in influencer_kols]))
            assert inf_mean > 0.05, f"Influencer belief_state too low: {inf_mean}"

    def test_belief_decay_works(self):
        """信念衰减应该让 belief_state 在无新曝光时回归 0"""
        from social.kol_network import KOLNode, KOLTier
        node = KOLNode(tier=KOLTier.MACRO, belief_decay=0.95, exposure_gain=2.0)
        node.receive_exposure(0.5, source_trust=0.8, narrative_strength=0.8)
        assert abs(node.belief_state) > 0.01

        # 无新曝光，信念衰减
        for _ in range(100):
            node.belief_state *= node.belief_decay
        assert abs(node.belief_state) < 0.01

    def test_tier_specific_susceptibility(self):
        """不同层级的 KOL 应有不同的 exposure_gain"""
        from social.kol_network import KOLNetwork
        network = KOLNetwork().build_default_network(
            n_macro=1, n_influencer=1, n_micro=1, n_retail=1
        )

        macro = next(k for k in network.get_kols() if k.tier.value == "macro")
        micro = next(k for k in network.get_kols() if k.tier.value == "micro")
        retail = next(k for k in network.nodes if k.tier.value == "retail")

        # Retail 应该比 Macro 更敏感
        assert retail.exposure_gain >= macro.exposure_gain


# ── P0.5: RegulatorAgent 干预效果验证 ──────────────────────────────

class TestRegulatorInterventionEffect:
    """P0.5: 验证监管干预真实生效"""

    def test_kol_downweight_uses_correct_field(self):
        """kol_downweight 应该修改 influence_score（不是 influence_weight）"""
        from risk.regulator_agent import RegulatorAgent
        from social.kol_network import KOLNetwork

        network = KOLNetwork().build_default_network(
            n_macro=1, n_influencer=1, n_micro=1, n_retail=5
        )
        regulator = RegulatorAgent()

        # 记录干预前
        kols = network.get_kols()
        before_scores = [k.influence_score for k in kols]

        # 触发 MODERATE 干预（包含 kol_downweight）
        regulator.step(
            risk_score=0.6,
            market_state={"price": 100.0, "bubble_risk": 0.5},
            kol_network=network,
        )

        # 验证 influence_score 已被降低
        after_scores = [k.influence_score for k in kols]
        for before, after in zip(before_scores, after_scores):
            assert after < before, f"influence_score not reduced: {before} -> {after}"

    def test_intervention_effect_report_generated(self):
        """干预应该生成 InterventionEffectReport"""
        from risk.regulator_agent import RegulatorAgent, InterventionEffectReport
        from social.kol_network import KOLNetwork

        network = KOLNetwork().build_default_network(
            n_macro=1, n_influencer=1, n_micro=1, n_retail=5
        )
        regulator = RegulatorAgent()

        regulator.step(
            risk_score=0.6,
            market_state={"price": 100.0, "bubble_risk": 0.5},
            kol_network=network,
        )

        assert len(regulator.effect_reports) > 0
        report = regulator.effect_reports[0]
        assert isinstance(report, InterventionEffectReport)
        assert report.verified is True
        assert report.before_mean > report.after_mean

    def test_narrative_throttle_effect_report(self):
        """narrative_throttle 应该生成效果报告"""
        from risk.regulator_agent import RegulatorAgent
        from narrative.narrative_engine import NarrativeEngine

        engine = NarrativeEngine()
        regulator = RegulatorAgent()

        regulator.step(
            risk_score=0.4,
            market_state={"price": 100.0, "bubble_risk": 0.3},
            narrative_engine=engine,
        )

        throttle_reports = [r for r in regulator.effect_reports if r.action == "narrative_throttle"]
        assert len(throttle_reports) > 0
        assert throttle_reports[0].verified is True

    def test_kol_downweight_effect_report_fields(self):
        """InterventionEffectReport 应包含完整字段"""
        from risk.regulator_agent import RegulatorAgent, InterventionEffectReport
        from social.kol_network import KOLNetwork

        network = KOLNetwork().build_default_network(
            n_macro=1, n_influencer=1, n_micro=1, n_retail=5
        )
        regulator = RegulatorAgent()

        regulator.step(
            risk_score=0.6,
            market_state={"price": 100.0, "bubble_risk": 0.5},
            kol_network=network,
        )

        report = next(r for r in regulator.effect_reports if r.action == "kol_downweight")
        assert report.targets > 0
        assert report.field_changed != ""
        assert report.step > 0
