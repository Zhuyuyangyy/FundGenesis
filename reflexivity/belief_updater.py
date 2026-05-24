"""
reflexivity/belief_updater.py
==============================
反身性信念更新机制
"""

from typing import List
from agents.base_agent import BaseAgent
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField


def update_agent_beliefs(agents: List[BaseAgent], market: MarketEnvironment,
                         emotion: EmotionField, herding_pressure: float = 0.0):
    """
    统一信念更新：每个 Agent 根据价格变化、羊群压力和情绪更新信念。

    信念更新公式：
    belief_new = α·belief_old + β·price_change + γ·herding_pressure + δ·emotion_factor

    参数：
    - α=0.6（信念惯性）
    - β=0.2（价格验证）
    - γ=0.1（羊群）
    - δ=0.1（情绪）
    """
    price_change = market.price_change_pct if market.price_history else 0.0
    emotion_factor = emotion.fear_greed_index * 0.1

    for agent in agents:
        old_belief = agent.belief
        agent.belief = (
            0.6 * old_belief
            + 0.2 * price_change
            + 0.1 * herding_pressure
            + emotion_factor
        )
        agent.belief = max(-1.0, min(1.0, agent.belief))


def compute_market_herding_pressure(agents: List[BaseAgent]) -> float:
    """
    计算市场级羊群压力：Agent 信念的平均方向。
    > 0 = 市场整体看多
    < 0 = 市场整体看空
    """
    if not agents:
        return 0.0
    return sum(a.belief for a in agents) / len(agents)


def detect_bubble_crash(market: MarketEnvironment, window: int = 30) -> str:
    """
    检测泡沫或崩盘信号。

    泡沫（bubble）：价格在短期内快速上涨且波动性低
    崩盘（crash）：价格急跌且波动性高
    """
    if len(market.price_history) < window:
        return "none"

    recent = market.price_history[-window:]
    recent_returns = market.returns_history[-window:] if market.returns_history else [0] * window

    price_change = (recent[-1] - recent[0]) / recent[0]
    avg_volatility = sum(abs(r) for r in recent_returns) / len(recent_returns)

    if price_change > 0.15 and avg_volatility < 0.03:
        return "bubble"
    elif price_change < -0.15 and avg_volatility > 0.05:
        return "crash"
    return "none"
