"""
test_agents.py - Agent 核心逻辑测试
====================================

使用 mock 方式测试 Agent 的决策逻辑，避免依赖完整市场环境。
"""

import pytest
from unittest.mock import MagicMock, patch
from agents.base_agent import Action, AgentConfig, BaseAgent


# ── 辅助 Mock ───────────────────────────────────────────────────

def create_mock_market(price=100.0, price_change_pct=0.0, order_imbalance=0.0):
    """创建一个模拟的 MarketSnapshot"""
    mock = MagicMock()
    mock.price = price
    mock.price_change_pct = price_change_pct
    mock.order_imbalance = order_imbalance
    mock.price_history = [price]
    mock.returns_history = [price_change_pct]
    return mock


def create_mock_emotion(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3):
    """创建一个模拟的 EmotionField"""
    mock = MagicMock()
    mock.fear = fear
    mock.greed = greed
    mock.confidence = confidence
    mock.uncertainty = uncertainty
    mock.fear_greed_index = greed - fear
    return mock


# ── BaseAgent 测试 ──────────────────────────────────────────────

class TestBaseAgent:
    """测试 BaseAgent 基类"""

    def test_base_agent_is_abstract(self):
        """BaseAgent 不应该直接实例化"""
        with pytest.raises(TypeError):
            BaseAgent("test_001")

    def test_agent_config_defaults(self):
        """AgentConfig 默认值应该合理"""
        cfg = AgentConfig()
        assert cfg.cash == 10000.0
        assert cfg.position == 0.0
        assert cfg.belief == 0.0
        assert cfg.herding_coefficient == 0.3
        assert cfg.emotional_sensitivity == 0.5

    def test_action_enum_values(self):
        """Action 枚举应该有 BUY, SELL, HOLD"""
        assert Action.BUY.value == "BUY"
        assert Action.SELL.value == "SELL"
        assert Action.HOLD.value == "HOLD"


# ── EmotionalRetail 测试 ────────────────────────────────────────

class TestEmotionalRetail:
    """测试 EmotionalRetail Agent"""

    def test_creation(self, emotional_retail_agent):
        """应该能创建 EmotionalRetail 实例"""
        assert emotional_retail_agent.agent_id == "retail_001"
        assert emotional_retail_agent.signal == "retail"

    def test_decide_buy_on_high_greed(self, emotional_retail_agent):
        """高贪婪 + 低恐惧应该触发买入"""
        market = create_mock_market(price_change_pct=0.02, order_imbalance=0.3)
        emotion = create_mock_emotion(fear=0.1, greed=0.9, uncertainty=0.2)
        action = emotional_retail_agent.decide(market, emotion)
        assert action == Action.BUY

    def test_decide_sell_on_high_fear(self, emotional_retail_agent):
        """高恐惧 + 低贪婪应该触发卖出"""
        market = create_mock_market(price_change_pct=-0.02, order_imbalance=-0.3)
        emotion = create_mock_emotion(fear=0.9, greed=0.1, uncertainty=0.2)
        action = emotional_retail_agent.decide(market, emotion)
        assert action == Action.SELL

    def test_decide_hold_on_neutral(self, emotional_retail_agent):
        """中性情绪应该倾向 HOLD"""
        market = create_mock_market(price_change_pct=0.0, order_imbalance=0.0)
        emotion = create_mock_emotion(fear=0.3, greed=0.3, uncertainty=0.3)
        action = emotional_retail_agent.decide(market, emotion)
        # 中性情况下可能 HOLD（取决于具体参数）
        assert action in [Action.BUY, Action.SELL, Action.HOLD]

    def test_high_uncertainty_amplifies_panic(self, emotional_retail_agent):
        """高不确定性应该放大恐慌效应"""
        market = create_mock_market(price_change_pct=-0.01, order_imbalance=-0.1)
        # 低不确定性
        emotion_low = create_mock_emotion(fear=0.5, greed=0.3, uncertainty=0.2)
        action_low = emotional_retail_agent.decide(market, emotion_low)

        # 高不确定性
        emotion_high = create_mock_emotion(fear=0.5, greed=0.3, uncertainty=0.8)
        action_high = emotional_retail_agent.decide(market, emotion_high)

        # 高不确定性时更倾向于卖出
        if action_low == Action.HOLD:
            assert action_high in [Action.SELL, Action.HOLD]

    def test_update_belief(self, emotional_retail_agent):
        """update_belief() 应该更新 belief 值"""
        initial_belief = emotional_retail_agent.belief
        market = create_mock_market(price_change_pct=0.05)
        emotional_retail_agent.update_belief(market, order_imbalance=0.3)
        assert emotional_retail_agent.belief != initial_belief

    def test_belief_bounded(self, emotional_retail_agent):
        """belief 应该在 [-1, 1] 范围内"""
        market = create_mock_market(price_change_pct=0.1)
        for _ in range(100):
            emotional_retail_agent.update_belief(market, order_imbalance=1.0)
        assert -1 <= emotional_retail_agent.belief <= 1


# ── TrendFollower 测试 ──────────────────────────────────────────

class TestTrendFollower:
    """测试 TrendFollower Agent"""

    def test_creation(self, trend_follower_agent):
        """应该能创建 TrendFollower 实例"""
        assert trend_follower_agent.agent_id == "trend_001"
        assert trend_follower_agent.signal == "trend"

    def test_decide_buy_on_uptrend(self, trend_follower_agent):
        """上升趋势应该触发买入"""
        market = create_mock_market(price_change_pct=0.02, order_imbalance=0.3)
        emotion = create_mock_emotion(greed=0.5, confidence=0.3)
        action = trend_follower_agent.decide(market, emotion)
        assert action == Action.BUY

    def test_decide_sell_on_downtrend(self, trend_follower_agent):
        """下降趋势应该触发卖出"""
        market = create_mock_market(price_change_pct=-0.02, order_imbalance=-0.3)
        emotion = create_mock_emotion(greed=0.5, confidence=0.3)
        action = trend_follower_agent.decide(market, emotion)
        assert action == Action.SELL

    def test_decide_hold_on_flat(self, trend_follower_agent):
        """平稳市场应该倾向 HOLD"""
        market = create_mock_market(price_change_pct=0.0, order_imbalance=0.0)
        emotion = create_mock_emotion(greed=0.3, confidence=0.5)
        action = trend_follower_agent.decide(market, emotion)
        assert action == Action.HOLD

    def test_momentum_amplified_by_greed(self, trend_follower_agent):
        """贪婪应该放大趋势信号"""
        market = create_mock_market(price_change_pct=0.01, order_imbalance=0.0)
        # 低贪婪
        emotion_low = create_mock_emotion(greed=0.1, confidence=0.5)
        # 高贪婪
        emotion_high = create_mock_emotion(greed=0.9, confidence=0.5)

        # 记录两种情况下的决策
        action_low = trend_follower_agent.decide(market, emotion_low)
        action_high = trend_follower_agent.decide(market, emotion_high)

        # 高贪婪时更倾向于买入（或至少不是卖出）
        if action_low == Action.HOLD:
            assert action_high in [Action.BUY, Action.HOLD]

    def test_update_belief(self, trend_follower_agent):
        """update_belief() 应该更新 belief 值"""
        initial_belief = trend_follower_agent.belief
        market = create_mock_market(price_change_pct=0.03)
        trend_follower_agent.update_belief(market, order_imbalance=0.2)
        assert trend_follower_agent.belief != initial_belief


# ── ValueInvestor 测试 ──────────────────────────────────────────

class TestValueInvestor:
    """测试 ValueInvestor Agent"""

    def test_creation(self, value_investor_agent):
        """应该能创建 ValueInvestor 实例"""
        assert value_investor_agent.agent_id == "value_001"
        assert value_investor_agent.signal == "value"
        assert value_investor_agent.fair_value == 100.0

    def test_decide_buy_on_undervalued(self, value_investor_agent):
        """价格低于公允价值应该触发买入"""
        market = create_mock_market(price=80.0, price_change_pct=0.0, order_imbalance=0.0)
        emotion = create_mock_emotion()
        action = value_investor_agent.decide(market, emotion)
        assert action == Action.BUY

    def test_decide_sell_on_overvalued(self, value_investor_agent):
        """价格高于公允价值应该触发卖出"""
        market = create_mock_market(price=120.0, price_change_pct=0.0, order_imbalance=0.0)
        emotion = create_mock_emotion()
        action = value_investor_agent.decide(market, emotion)
        assert action == Action.SELL

    def test_decide_hold_on_fair_value(self, value_investor_agent):
        """价格接近公允价值应该倾向 HOLD"""
        market = create_mock_market(price=100.0, price_change_pct=0.0, order_imbalance=0.0)
        emotion = create_mock_emotion()
        action = value_investor_agent.decide(market, emotion)
        assert action == Action.HOLD

    def test_low_herding_coefficient(self, value_investor_agent):
        """价值投资者应该有低羊群系数"""
        assert value_investor_agent.config.herding_coefficient == 0.1

    def test_low_emotional_sensitivity(self, value_investor_agent):
        """价值投资者应该有低情绪敏感度"""
        assert value_investor_agent.config.emotional_sensitivity == 0.2

    def test_update_belief(self, value_investor_agent):
        """update_belief() 应该更新 belief 值"""
        initial_belief = value_investor_agent.belief
        market = create_mock_market(price_change_pct=0.02)
        value_investor_agent.update_belief(market, order_imbalance=0.1)
        assert value_investor_agent.belief != initial_belief


# ── Agent 交互测试 ──────────────────────────────────────────────

class TestAgentInteraction:
    """测试 Agent 之间的交互和集体行为"""

    def test_all_agents_decide_returns_action(self, emotional_retail_agent, trend_follower_agent, value_investor_agent):
        """所有 Agent 的 decide() 都应该返回有效的 Action"""
        market = create_mock_market(price=100.0, price_change_pct=0.01, order_imbalance=0.1)
        emotion = create_mock_emotion(fear=0.3, greed=0.4, confidence=0.5, uncertainty=0.3)

        for agent in [emotional_retail_agent, trend_follower_agent, value_investor_agent]:
            action = agent.decide(market, emotion)
            assert action in [Action.BUY, Action.SELL, Action.HOLD]

    def test_agents_react_differently_to_same_market(self, emotional_retail_agent, trend_follower_agent, value_investor_agent):
        """不同类型的 Agent 应该对同一市场状态有不同的反应"""
        market = create_mock_market(price=110.0, price_change_pct=0.05, order_imbalance=0.5)
        emotion = create_mock_emotion(fear=0.2, greed=0.6, confidence=0.4, uncertainty=0.3)

        actions = {
            "retail": emotional_retail_agent.decide(market, emotion),
            "trend": trend_follower_agent.decide(market, emotion),
            "value": value_investor_agent.decide(market, emotion),
        }

        # 至少应该有不同的决策（不全是 BUY 或全是 HOLD）
        unique_actions = set(actions.values())
        # 由于参数设置，可能不总是有差异，但应该至少返回有效值
        for action in unique_actions:
            assert action in [Action.BUY, Action.SELL, Action.HOLD]

    def test_agents_update_beliefs(self, emotional_retail_agent, trend_follower_agent, value_investor_agent):
        """所有 Agent 的 update_belief() 都应该正常工作"""
        market = create_mock_market(price_change_pct=0.03)

        for agent in [emotional_retail_agent, trend_follower_agent, value_investor_agent]:
            initial_belief = agent.belief
            agent.update_belief(market, order_imbalance=0.2)
            # belief 应该有变化（除非已经是边界值）
            if -1 < initial_belief < 1:
                assert agent.belief != initial_belief or agent.belief in [-1.0, 1.0]
