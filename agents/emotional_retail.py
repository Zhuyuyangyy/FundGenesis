"""
agents/emotional_retail.py
==========================
情绪化散户：被 FOMO 和恐慌支配，最容易被情绪左右
"""

from agents.base_agent import BaseAgent, Action, AgentConfig


class EmotionalRetail(BaseAgent):
    """
    情绪化散户：
    - 信息滞后
    - FOMO 驱动买入
    - 恐慌驱动卖出
    - 羊群效应最强
    - 高不确定性时更容易踩踏
    """

    signal = "retail"

    def __init__(self, agent_id: str, fomo_sensitivity: float = 1.5,
                 panic_sensitivity: float = 2.0, info_lag: float = 0.5,
                 config: AgentConfig = None):
        super().__init__(agent_id, config)
        self.fomo_sensitivity = fomo_sensitivity
        self.panic_sensitivity = panic_sensitivity
        self.info_lag = info_lag  # 信息滞后因子
        self.config.herding_coefficient = 0.7
        self.config.emotional_sensitivity = 0.8

    def decide(self, market, emotion) -> Action:
        # FOMO 因子（害怕错过上涨）
        fomo = emotion.greed * self.fomo_sensitivity

        # 恐慌因子（害怕亏损）
        panic = emotion.fear * self.panic_sensitivity

        # 信息滞后的价格变化
        delayed_change = (market.price_change_pct if market.price_history else 0.0) * self.info_lag

        # 综合得分
        score = fomo - panic + delayed_change * 0.5

        # 高不确定性时恐慌加剧
        if emotion.uncertainty > 0.6:
            score -= emotion.uncertainty * panic * 0.5

        # 羊群因子
        herding = self.config.herding_coefficient * market.order_imbalance * 0.5
        score += herding

        if score > 0.1:
            return Action.BUY
        elif score < -0.1:
            return Action.SELL
        return Action.HOLD

    def update_belief(self, market, order_imbalance: float):
        price_change = market.price_change_pct if market.price_history else 0.0
        herding = self.config.herding_coefficient * order_imbalance
        emotion_influence = self.config.emotional_sensitivity * (
            (market.returns_history[-1] if market.returns_history else 0.0))
        self.belief = 0.4 * self.belief + 0.2 * price_change + 0.2 * herding + 0.2 * emotion_influence
        self.belief = max(-1.0, min(1.0, self.belief))


# Alias for V0.2 experiment compatibility
EmotionalRetailAgent = EmotionalRetail
