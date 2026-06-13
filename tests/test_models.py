"""
test_models.py - 数据模型测试
==============================

测试核心数据模型的行为和边界条件。
"""

import pytest
import math
import numpy as np


# ── EmotionField 测试 ───────────────────────────────────────────

class TestEmotionField:
    """测试 EmotionField 数据模型"""

    def test_emotion_field_creation(self):
        """应该能创建 EmotionField 实例"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.5, greed=0.3, confidence=0.6, uncertainty=0.2)
        assert ef.fear == 0.5
        assert ef.greed == 0.3
        assert ef.confidence == 0.6
        assert ef.uncertainty == 0.2

    def test_emotion_field_normalize_clamps_values(self):
        """normalize() 应该将值限制在 [0, 1] 范围内"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=1.5, greed=-0.1, confidence=0.5, uncertainty=0.3)
        ef.normalize()
        assert 0 <= ef.fear <= 1
        assert 0 <= ef.greed <= 1
        assert 0 <= ef.confidence <= 1
        assert 0 <= ef.uncertainty <= 1

    def test_emotion_field_to_vector(self):
        """to_vector() 应该返回 4 元素列表"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.1, greed=0.2, confidence=0.3, uncertainty=0.4)
        vec = ef.to_vector()
        assert len(vec) == 4
        assert vec == [0.1, 0.2, 0.3, 0.4]

    def test_fear_greed_index(self):
        """fear_greed_index 应该是 greed - fear"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.3, greed=0.7)
        assert ef.fear_greed_index == pytest.approx(0.4)

    def test_emotion_factor_range(self):
        """emotion_factor() 应该返回合理范围的值"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)
        factor = ef.emotion_factor()
        assert -1.0 <= factor <= 1.0

    def test_apply_price_change_positive(self):
        """正价格变化应该增加贪婪、减少恐惧"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.5, greed=0.3, confidence=0.5, uncertainty=0.3)
        initial_greed = ef.greed
        initial_fear = ef.fear
        ef.apply_price_change(0.05)
        assert ef.greed > initial_greed
        assert ef.fear < initial_fear

    def test_apply_price_change_negative(self):
        """负价格变化应该增加恐惧、减少贪婪"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.3, greed=0.5, confidence=0.5, uncertainty=0.3)
        initial_greed = ef.greed
        initial_fear = ef.fear
        ef.apply_price_change(-0.05)
        assert ef.fear > initial_fear
        assert ef.greed < initial_greed

    def test_apply_shock_positive(self):
        """正冲击应该增加贪婪和信心"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)
        initial_greed = ef.greed
        initial_confidence = ef.confidence
        ef.apply_shock(0.5)
        assert ef.greed > initial_greed
        assert ef.confidence > initial_confidence

    def test_apply_shock_negative(self):
        """负冲击应该增加恐惧和不确定性"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)
        initial_fear = ef.fear
        initial_uncertainty = ef.uncertainty
        ef.apply_shock(-0.5)
        assert ef.fear > initial_fear
        assert ef.uncertainty > initial_uncertainty

    def test_decay_toward_neutral(self):
        """decay_toward_neutral() 应该将值推向中性"""
        from core.emotion_field import EmotionField
        ef = EmotionField(fear=0.9, greed=0.9, confidence=0.9, uncertainty=0.9)
        for _ in range(100):
            ef.decay_toward_neutral(inertia=0.9)
        # 经过足够多的衰减，值应该接近中性
        assert ef.fear < 0.5
        assert ef.greed < 0.5
        assert ef.confidence < 0.7

    def test_emotion_field_copy(self):
        """copy() 应该创建独立副本"""
        from core.emotion_field import EmotionField
        ef1 = EmotionField(fear=0.5, greed=0.3, confidence=0.6, uncertainty=0.2)
        ef2 = ef1.copy()
        assert ef1.fear == ef2.fear
        ef2.fear = 0.9
        assert ef1.fear != ef2.fear


# ── MarketMetrics 测试 ──────────────────────────────────────────

class TestMarketMetrics:
    """测试 MarketMetrics 数据模型"""

    def test_bubble_indicator_normal(self):
        """bubble_indicator 在价格等于基本面时应该为 0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_bubble_indicator(100.0, 100.0) == pytest.approx(0.0)

    def test_bubble_indicator_overpriced(self):
        """价格高于基本面时 bubble_indicator > 0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_bubble_indicator(120.0, 100.0) > 0

    def test_bubble_indicator_underpriced(self):
        """价格低于基本面时 bubble_indicator < 0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_bubble_indicator(80.0, 100.0) < 0

    def test_bubble_indicator_zero_fundamental(self):
        """基本面为 0 时应该返回 0（避免除零）"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_bubble_indicator(100.0, 0.0) == 0.0

    def test_order_imbalance_balanced(self):
        """买卖平衡时 order_imbalance 应该为 0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_order_imbalance(50.0, 50.0) == pytest.approx(0.0)

    def test_order_imbalance_buy_dominant(self):
        """买方主导时 order_imbalance > 0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_order_imbalance(80.0, 20.0) > 0

    def test_order_imbalance_sell_dominant(self):
        """卖方主导时 order_imbalance < 0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_order_imbalance(20.0, 80.0) < 0

    def test_order_imbalance_no_volume(self):
        """无交易量时 order_imbalance 应该为 0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_order_imbalance(0.0, 0.0) == 0.0

    def test_price_efficiency_with_returns(self):
        """price_efficiency 应该返回非负值"""
        from core.metrics import MarketMetrics
        returns = [0.01, -0.02, 0.03, -0.01, 0.02]
        eff = MarketMetrics.compute_price_efficiency(returns)
        assert eff >= 0

    def test_price_efficiency_empty_returns(self):
        """空收益率列表应该返回 1.0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_price_efficiency([]) == 1.0

    def test_price_efficiency_single_return(self):
        """单个收益率应该返回 1.0"""
        from core.metrics import MarketMetrics
        assert MarketMetrics.compute_price_efficiency([0.01]) == 1.0


# ── MarketSnapshot 测试 ─────────────────────────────────────────

class TestMarketSnapshot:
    """测试 MarketSnapshot 数据模型"""

    def test_snapshot_creation(self, market):
        """应该能从 MarketEnvironment 创建快照"""
        snapshot = market.get_snapshot()
        assert snapshot.price == 100.0
        assert len(snapshot.price_history) == 1
        assert snapshot.price_change_pct == 0.0

    def test_snapshot_is_independent(self, market):
        """快照应该是独立的（不随市场变化）"""
        snapshot1 = market.get_snapshot()
        market.price = 200.0
        snapshot2 = market.get_snapshot()
        assert snapshot1.price == 100.0
        assert snapshot2.price == 200.0


# ── KOLNode 测试 ────────────────────────────────────────────────

class TestKOLNode:
    """测试 KOLNode 数据模型"""

    def test_kol_node_creation(self):
        """应该能创建 KOLNode 实例"""
        from social.kol_network import KOLNode, KOLTier
        node = KOLNode(
            node_id="test_001",
            tier=KOLTier.MACRO,
            name="TestKOL",
            influence_score=0.8,
            trust_level=0.7,
        )
        assert node.node_id == "test_001"
        assert node.tier == KOLTier.MACRO
        assert node.is_kol is True

    def test_kol_node_is_kol_property(self):
        """is_kol 属性应该正确识别 KOL 类型"""
        from social.kol_network import KOLNode, KOLTier
        macro = KOLNode(tier=KOLTier.MACRO)
        retail = KOLNode(tier=KOLTier.RETAIL)
        assert macro.is_kol is True
        assert retail.is_kol is False

    def test_kol_node_receive_exposure(self):
        """receive_exposure() 应该增加 narrative_exposure"""
        from social.kol_network import KOLNode, KOLTier
        node = KOLNode(tier=KOLTier.RETAIL, susceptibility=0.5)
        initial_exposure = node.narrative_exposure
        node.receive_exposure(0.5)
        assert node.narrative_exposure > initial_exposure

    def test_kol_node_reset_exposure(self):
        """reset_exposure() 应该衰减 exposure"""
        from social.kol_network import KOLNode, KOLTier
        node = KOLNode(tier=KOLTier.RETAIL, narrative_exposure=0.8)
        node.reset_exposure(decay=0.5)
        assert node.narrative_exposure == pytest.approx(0.4)


# ── MarketEnvironment 测试 ──────────────────────────────────────

class TestMarketEnvironment:
    """测试 MarketEnvironment 数据模型"""

    def test_market_reset(self, market):
        """reset() 应该重置所有状态"""
        market.price = 200.0
        market.step_count = 50
        market.reset(initial_price=100.0)
        assert market.price == 100.0
        assert market.step_count == 0
        assert len(market.price_history) == 1

    def test_submit_order_buy(self, market):
        """买入订单应该增加 buy_volume"""
        market.submit_order("agent_1", "BUY", 0.1)
        assert market.buy_volume == pytest.approx(0.1)

    def test_submit_order_sell(self, market):
        """卖出订单应该增加 sell_volume"""
        market.submit_order("agent_1", "SELL", 0.1)
        assert market.sell_volume == pytest.approx(0.1)

    def test_submit_order_hold(self, market):
        """HOLD 订单不应该改变任何 volume"""
        market.submit_order("agent_1", "HOLD", 0.1)
        assert market.buy_volume == 0.0
        assert market.sell_volume == 0.0

    def test_net_demand(self, market):
        """net_demand 应该是 buy_volume - sell_volume"""
        market.submit_order("a1", "BUY", 0.3)
        market.submit_order("a2", "SELL", 0.1)
        assert market.net_demand == pytest.approx(0.2)

    def test_order_imbalance(self, market):
        """order_imbalance 应该在 [-1, 1] 范围内"""
        market.submit_order("a1", "BUY", 0.8)
        market.submit_order("a2", "SELL", 0.2)
        oi = market.order_imbalance
        assert -1 <= oi <= 1
        assert oi > 0  # 买方主导

    def test_apply_shock(self, market):
        """apply_shock() 应该改变价格"""
        initial_price = market.price
        market.apply_shock(0.1)  # 10% 上涨
        assert market.price > initial_price

    def test_apply_shock_negative(self, market):
        """负冲击应该降低价格"""
        initial_price = market.price
        market.apply_shock(-0.1)  # 10% 下跌
        assert market.price < initial_price

    def test_update_price_increments_step(self, market, emotion):
        """update_price() 应该增加 step_count"""
        initial_step = market.step_count
        market.update_price(emotion)
        assert market.step_count == initial_step + 1

    def test_get_volatility(self, market):
        """get_volatility() 应该返回非负值"""
        vol = market.get_volatility()
        assert vol >= 0
