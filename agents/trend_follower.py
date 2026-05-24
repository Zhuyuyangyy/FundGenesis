"""
agents/trend_follower.py
========================
趋势交易者：追涨杀跌，顺势而为，有一定羊群效应
"""

from agents.base_agent import BaseAgent, Action, AgentConfig


class TrendFollower(BaseAgent):
    """
    趋势交易者：
    - 主要跟随价格动量
    - 情绪放大趋势信号
    - 有中等羊群效应
    """

    signal = "trend"

    def __init__(self, agent_id: str, momentum_weight: float = 3.0,
                 config: AgentConfig = None):
        super().__init__(agent_id, config)
        self.momentum_weight = momentum_weight
        self.config.herding_coefficient = 0.4
        self.config.emotional_sensitivity = 0.4

    def decide(self, market, emotion) -> Action:
        # 趋势因子（主要驱动）
        price_change = market.price_change_pct if market.price_history else 0.0
        trend_signal = price_change * self.momentum_weight

        # 情绪放大
        emotion_amplifier = 1.0 + emotion.greed * 0.5 - emotion.confidence * 0.3
        trend_signal *= emotion_amplifier

        # 羊群因子
        herding = self.config.herding_coefficient * market.order_imbalance

        score = trend_signal + herding

        if score > 0.03:
            return Action.BUY
        elif score < -0.03:
            return Action.SELL
        return Action.HOLD

    def update_belief(self, market, order_imbalance: float):
        price_change = market.price_change_pct if market.price_history else 0.0
        herding = self.config.herding_coefficient * order_imbalance
        self.belief = 0.5 * self.belief + 0.3 * price_change + 0.2 * herding
        self.belief = max(-1.0, min(1.0, self.belief))


# Alias for V0.2 experiment compatibility
TrendFollowerAgent = TrendFollower
