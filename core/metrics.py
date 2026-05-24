"""
core/metrics.py
===============
市场级指标计算：波动率、订单不平衡度、泡沫指标等
"""

from dataclasses import dataclass
import math


@dataclass
class MarketMetrics:
    """某时刻市场状态快照"""
    step: int
    price: float
    price_change_pct: float     # 本步价格变化率
    cumulative_return: float     # 累计收益率
    volatility: float            # 已实现波动率（滚动窗口）
    order_imbalance: float       # 订单不平衡度 (BUY-SELL)/Total
    herding_index: float         # 羊群效应指标
    bubble_indicator: float      # 泡沫指标（偏离基本面程度）
    fear_greed_index: float     # 恐贪指数
    price_efficiency: float      # 价格效率指标

    @staticmethod
    def compute_bubble_indicator(price: float, fundamental_value: float) -> float:
        """
        泡沫指标：价格偏离基本面价值的程度。
        > 0 = 价格高于基本面（可能泡沫）
        < 0 = 价格低于基本面（可能价值陷阱）
        范围不做限制，数值越大泡沫/低估越严重。
        """
        if fundamental_value <= 0:
            return 0.0
        return (price - fundamental_value) / fundamental_value

    @staticmethod
    def compute_order_imbalance(buy_volume: float, sell_volume: float) -> float:
        """
        订单不平衡度。
        范围 [-1, 1]：
        > 0 = 买方主导
        < 0 = 卖方主导
        = 0 = 多空平衡
        """
        total = buy_volume + sell_volume
        if total == 0:
            return 0.0
        return (buy_volume - sell_volume) / total

    @staticmethod
    def compute_price_efficiency(returns: list[float]) -> float:
        """
        价格效率：收益率序列的均值/标准差比值。
        越高表示价格越"有效"，越跟随基本面信息。
        """
        if len(returns) < 2:
            return 1.0
        mean_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - mean_ret) ** 2 for r in returns) / len(returns))
        if std_ret == 0:
            return 0.0
        return abs(mean_ret) / std_ret
