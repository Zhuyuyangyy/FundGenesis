"""
agents/value_investor.py
========================
价值投资者：基于估值偏离决定买卖，逆向交易
"""

from agents.base_agent import BaseAgent, Action, AgentConfig


class ValueInvestor(BaseAgent):
    """
    价值投资者：
    - 价格 < 基本面价值 → 买入（低估）
    - 价格 > 基本面价值 → 卖出（高估）
    - 持仓周期长，换手率低
    - 羊群效应低，情绪敏感度低
    """

    signal = "value"

    def __init__(self, agent_id: str, fair_value: float = 100.0,
                 sensitivity: float = 2.0, config: AgentConfig = None):
        super().__init__(agent_id, config)
        self.fair_value = fair_value
        self.sensitivity = sensitivity  # 对估值偏离的反应强度
        self.config.herding_coefficient = 0.1
        self.config.emotional_sensitivity = 0.2

    def decide(self, market, emotion) -> Action:
        # 估值偏离
        deviation = (market.price - self.fair_value) / self.fair_value
        value_signal = -deviation * self.sensitivity

        # 趋势因子（弱）
        momentum = market.price_change_pct if market.price_history else 0.0

        # 情绪因子
        emotion_factor = emotion.fear_greed_index * self.config.emotional_sensitivity

        # 综合得分
        score = 0.65 * value_signal + 0.15 * momentum + 0.20 * emotion_factor

        # 阈值判断
        if score > 0.05:
            return Action.BUY
        elif score < -0.05:
            return Action.SELL
        return Action.HOLD

    def update_belief(self, market, order_imbalance: float):
        """
        信念更新：基于价格变化和周围订单不平衡度。
        价值投资者会参考订单簿但不过度跟随。
        """
        price_change = market.price_change_pct if market.price_history else 0.0
        herding = self.config.herding_coefficient * order_imbalance
        self.belief = 0.6 * self.belief + 0.3 * price_change + 0.1 * herding
        self.belief = max(-1.0, min(1.0, self.belief))


# Alias for V0.2 experiment compatibility
ValueInvestorAgent = ValueInvestor

