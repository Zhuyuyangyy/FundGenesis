"""
core/market_environment.py
==========================
虚拟市场环境：管理资产价格、持仓、订单撮合
"""

from dataclasses import dataclass, field
from typing import List
import random
import math
import numpy as np


@dataclass
class MarketSnapshot:
    """
    市场状态快照（只读视图）。
    传递给 Agent.decide()，避免暴露完整 MarketEnvironment。
    """
    price: float
    price_history: List[float]
    price_change_pct: float
    order_imbalance: float  # [-1, 1]
    returns_history: List[float]

from core.emotion_field import EmotionField
from core.metrics import MarketMetrics


@dataclass
class MarketEnvironment:
    """
    虚拟市场状态。
    V0.1 使用简化订单撮合：计算净买入压力，驱动价格变化。
    """
    # 资产状态
    price: float = 100.0
    initial_price: float = 100.0
    fundamental_value: float = 100.0  # 基本面价值（用于泡沫检测）

    # 历史
    price_history: list = field(default_factory=list)
    returns_history: list = field(default_factory=list)

    # 当步统计
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    price_change_pct: float = 0.0  # 最近一次价格变化率

    # P0.2: 区分 step-level 和 cumulative 统计
    step_net_demand: float = 0.0          # 当前步净需求（每步重置）
    cumulative_net_demand: float = 0.0    # 历史累计净需求（仅统计用）
    step_buy_volume: float = 0.0          # 当前步买入量
    step_sell_volume: float = 0.0         # 当前步卖出量

    # 配置参数
    impact_coefficient: float = 0.5  # η：价格对净需求的敏感度
    noise_std: float = 0.01          # ε_t 随机噪声标准差
    total_agents: int = 100         # Agent 总数（供监控使用）

    step_count: int = 0

    def reset(self, initial_price: float = 100.0,
              impact_coefficient: float = 0.5,
              noise_std: float = 0.01,
              total_agents: int = 100):
        self.price = initial_price
        self.initial_price = initial_price
        self.fundamental_value = initial_price
        self.price_history = [initial_price]
        self.returns_history = [0.0]
        self.buy_volume = 0.0
        self.sell_volume = 0.0
        self.step_net_demand = 0.0
        self.cumulative_net_demand = 0.0
        self.step_buy_volume = 0.0
        self.step_sell_volume = 0.0
        self.impact_coefficient = impact_coefficient
        self.noise_std = noise_std
        self.total_agents = total_agents
        self.step_count = 0

    def begin_step(self):
        """
        P0.2: 每步开始时调用，清空当步订单统计。
        必须在 agents_decide() 之前调用。
        """
        self.step_buy_volume = 0.0
        self.step_sell_volume = 0.0
        self.step_net_demand = 0.0
        # 注意：buy_volume/sell_volume 也清空（兼容旧调用方式）
        self.buy_volume = 0.0
        self.sell_volume = 0.0

    def end_step(self):
        """
        P0.2: 每步结束时调用，记录当步统计到累计值。
        必须在 update_price() 之后调用。
        """
        self.step_net_demand = self.step_buy_volume - self.step_sell_volume
        self.cumulative_net_demand += self.step_net_demand

    def reset_volumes(self):
        """向后兼容：等价于 begin_step() 的清空操作。"""
        self.begin_step()

    def submit_order(self, agent_id: str, action: str, volume: float):
        """
        Agent 提交订单。
        action: "BUY" / "SELL" / "HOLD"
        volume: 交易量（相对于总资金的归一化比例）
        """
        if action == "BUY":
            vol = max(0.0, volume)
            self.buy_volume += vol
            self.step_buy_volume += vol
        elif action == "SELL":
            vol = max(0.0, volume)
            self.sell_volume += vol
            self.step_sell_volume += vol

    def apply_shock(self, magnitude: float):
        """
        直接对价格施加冲击（用于黑天鹅等外部事件）。
        magnitude > 0 → 价格上涨
        magnitude < 0 → 价格下跌（绝对值越大跌得越多）
        """
        self.price = self.price * (1.0 + magnitude)
        self.price = max(self.price, 0.01)

    @property
    def net_demand(self) -> float:
        """净买入压力"""
        return self.buy_volume - self.sell_volume

    @property
    def order_imbalance(self) -> float:
        """订单不平衡度 [-1, 1]"""
        total = self.buy_volume + self.sell_volume
        if total == 0:
            return 0.0
        return (self.buy_volume - self.sell_volume) / total

    def update_price(self, emotion: EmotionField, max_step_return: float = 0.025):
        """
        根据净需求压力和情绪更新价格，加入基本面均值回复力。
        P_{t+1} = P_t · exp(η · order_imbalance_t + φ · deviation + ε_t)

        公式：
        - η · order_imbalance：羊群/趋势驱动的价格变化
        - φ · deviation：基本面偏离产生的均值回复力（防止泡沫/崩盘）
        - ε_t：高斯随机噪声
        """
        # 偏离基本面的程度（超过基本面则反向回复）
        deviation = (self.price - self.fundamental_value) / self.fundamental_value
        # 均值回复强度动态化：偏离越大力越强（类似弹簧）
        mean_reversion_strength = 0.03  # φ = 3%，基础回复力
        mean_reversion_breakpoint = 0.20  # 偏离超过20%后增强回复
        if abs(deviation) > mean_reversion_breakpoint:
            mean_reversion_strength = 0.10  # 深度偏离时加强回复

        # 情绪放大系数
        emotion_amp = 1.0 + emotion.greed * 0.2 - emotion.fear * 0.15
        effective_impact = self.impact_coefficient * emotion_amp

        # 订单不平衡度
        oi = self.order_imbalance  # [-1, 1]

        # 噪声
        noise = np.random.normal(0, self.noise_std)

        # 对数回报 = 情绪驱动 + 均值回复 + 噪声
        log_return = (
            effective_impact * oi
            - mean_reversion_strength * deviation
            + noise
        )

        # 限制单步最大变化
        log_return = max(-max_step_return, min(max_step_return, log_return))

        # 更新价格
        new_price = self.price * math.exp(log_return)
        new_price = max(new_price, 0.01)

        # 记录
        self.price_change_pct = (new_price - self.price) / self.price
        self.returns_history.append(self.price_change_pct)

        if len(self.returns_history) > 500:
            self.returns_history = self.returns_history[-500:]

        self.price = new_price
        self.price_history.append(new_price)
        self.step_count += 1

    def get_volatility(self, window: int = 50) -> float:
        """已实现波动率（滚动窗口）"""
        if len(self.returns_history) < 2:
            return self.noise_std
        recent = self.returns_history[-window:]
        mean_ret = sum(recent) / len(recent)
        variance = sum((r - mean_ret) ** 2 for r in recent) / len(recent)
        return math.sqrt(variance)

    @property
    def volatility(self) -> float:
        """当前市场波动率（供 ReflexivityMonitor 使用）"""
        return self.get_volatility()

    def get_snapshot(self) -> "MarketSnapshot":
        """
        返回市场状态快照，供 Agent.decide() 使用。
        这样可以避免直接传递 MarketEnvironment 引用。
        """
        return MarketSnapshot(
            price=self.price,
            price_history=list(self.price_history),
            price_change_pct=self.price_change_pct,
            order_imbalance=self.order_imbalance,
            returns_history=list(self.returns_history),
        )

    def get_metrics(self, emotion: EmotionField, step: int) -> MarketMetrics:
        """计算当前市场指标快照"""
        recent_returns = self.returns_history[-50:] if self.returns_history else [0.0]
        return MarketMetrics(
            step=step,
            price=self.price,
            price_change_pct=recent_returns[-1] if recent_returns else 0.0,
            cumulative_return=(self.price - self.initial_price) / self.initial_price,
            volatility=self.get_volatility(),
            order_imbalance=self.order_imbalance,
            herding_index=0.0,  # 由 ExperimentLab 注入
            bubble_indicator=MarketMetrics.compute_bubble_indicator(
                self.price, self.fundamental_value),
            fear_greed_index=emotion.fear_greed_index,
            price_efficiency=MarketMetrics.compute_price_efficiency(recent_returns),
            narrative_price_divergence=MarketMetrics.compute_narrative_price_divergence(
                recent_returns,
                emotion.fear_greed_index,
                abs(emotion.greed - 0.5) + abs(emotion.fear - 0.5),
            ),
        )

    def __repr__(self):
        return (f"Market(price={self.price:.2f}, "
                f"net_demand={self.net_demand:.4f}, "
                f"vol={self.get_volatility():.4f})")
