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
    narrative_price_divergence: float = 0.5  # 叙事-价格背离度 [0, 1]

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
        价格效率：收益率序列的均值/标准差比值（CV 倒数）。
        越高表示价格越"有效"，越跟随基本面信息。
        - len(returns) < 2 → 1.0（信息不足视为有效）
        - std == 0 且 mean == 0 → 1.0（无波动视为完全有效）
        - std == 0 且 mean != 0 → 0.0（无波动但有方向，信息可疑）
        - 其他：|mean| / std
        """
        if len(returns) < 2:
            return 1.0
        mean_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - mean_ret) ** 2 for r in returns) / len(returns))
        if std_ret == 0.0:
            # 无波动时，按方向性区分：纯平=有效，有偏移=无效
            return 1.0 if mean_ret == 0.0 else 0.0
        return abs(mean_ret) / std_ret

    @staticmethod
    def compute_narrative_price_divergence(
        recent_returns: list[float],
        narrative_polarity: float,
        narrative_strength: float,
    ) -> float:
        """
        叙事-价格背离度（Reflexivity Divergence Indicator）

        测量近期价格走势与主导叙事方向的一致性。是反身性反转的领先指标。
        - 0.0 = 完全确认：价格与叙事方向一致（强反身性循环中）
        - 0.5 = 中性：无叙事实质性影响，或无近期数据
        - 1.0 = 完全背离：价格与叙事方向相反（叙事即将失效 / 反转信号）

        计算逻辑：
          price_signal = tanh(mean_recent_return * 10)  ∈ (-1, 1)
          narrative_signal = clamp(narrative_polarity, -1, 1)
          direction_match = sign(price_signal) * sign(narrative_signal)
          divergence = 0.5 * (1 - direction_match) * narrative_strength
                       + 0.5 * (1 - |direction_match|) * (1 - |price_signal|)

        输出范围 [0, 1]。

        参数：
        - recent_returns: 近期收益率列表（建议 5-20 步窗口）
        - narrative_polarity: 叙事方向 [-1, 1]，正=利好，负=利空
        - narrative_strength: 叙事强度 [0, 1]，0 表示无有效叙事
        """
        if not recent_returns or narrative_strength <= 0.0:
            return 0.5

        mean_ret = sum(recent_returns) / len(recent_returns)
        # 压缩到 (-1, 1)，对大幅波动饱和
        price_signal = math.tanh(mean_ret * 10.0)
        # 叙事极性
        nar_signal = max(-1.0, min(1.0, narrative_polarity))

        # 方向对齐：+1=一致，-1=相反，0=中性
        if price_signal == 0.0 or nar_signal == 0.0:
            direction_match = 0.0
        else:
            ps = 1.0 if price_signal > 0.0 else -1.0
            ns = 1.0 if nar_signal > 0.0 else -1.0
            direction_match = ps * ns  # +1 一致, -1 相反

        # 背离 = 方向不一致 + 叙事强；或弱信号 + 弱价格
        divergence = 0.5 * (1.0 - direction_match) * narrative_strength \
                   + 0.5 * (1.0 - abs(direction_match)) * (1.0 - abs(price_signal))

        return max(0.0, min(1.0, divergence))
