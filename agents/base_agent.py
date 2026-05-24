"""
agents/base_agent.py
====================
Agent 基类：定义接口和公共属性
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class AgentConfig:
    """Agent 配置参数"""
    cash: float = 10000.0        # 初始现金
    position: float = 0.0        # 持仓数量
    belief: float = 0.0         # 信念值 [-1, 1]，正=看多，负=看空
    herding_coefficient: float = 0.3  # 羊群系数
    emotional_sensitivity: float = 0.5  # 情绪敏感度
    confirmation_bias: float = 0.3  # 确认偏误程度


class BaseAgent(ABC):
    """
    所有市场参与者的基类。
    V0.1 中每个 Agent 有固定的头寸，不做仓位管理。
    """

    signal: str = "base"  # Agent 类型标识

    def __init__(self, agent_id: str, config: AgentConfig = None):
        self.agent_id = agent_id
        self.config = config or AgentConfig()
        self.cash = self.config.cash
        self.position = self.config.position
        self.belief = self.config.belief

    @abstractmethod
    def decide(self, market, emotion) -> Action:
        """
        核心决策方法。
        market: MarketEnvironment 实例
        emotion: EmotionField 实例
        返回: Action.BUY / Action.SELL / Action.HOLD
        """
        pass

    def get_trade_volume(self) -> float:
        """
        返回本次交易量（归一化到 [0, 1]）。
        V0.1 简化：固定为 0.1（即 10% 资金/持仓）。
        子类可重写。
        """
        return 0.1

    def update_belief_from_price(self, price_change_pct: float):
        """
        根据价格变动更新信念（用于反身性反馈）。
        简单版：只看价格方向。
        """
        self.belief = 0.7 * self.belief + 0.3 * (1.0 if price_change_pct > 0 else -1.0)
        self.belief = max(-1.0, min(1.0, self.belief))

    def apply_transaction_cost(self, action: Action, price: float, volume: float):
        """简化交易成本计算（不实际扣费，仅影响决策判断）"""
        pass

    def __repr__(self):
        return f"{self.signal}(id={self.agent_id}, belief={self.belief:.2f})"
