"""
core/belief_updater_v2.py
===========================
V0.2 信念更新器：纳入叙事曝光、价格确认、社会压力、先验偏误。

V0.1 公式：
  belief_new = 0.6·belief_old + 0.2·price_change + 0.1·herding + 0.1·emotion

V0.2 公式：
  belief_new = α·belief_old
             + β·narrative_exposure·narrative_strength
             + γ·price_confirmation
             + δ·social_pressure
             - θ·contradiction_signal
             + ε·prior_bias

约束：
  叙事曝光需要先影响信念，信念再影响情绪，再影响行为，最后才影响价格。
  这是反身性，不是即时因果。
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from agents.base_agent import BaseAgent
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from social.kol_network import KOLNetwork
from narrative.narrative_engine import NarrativeEngine


@dataclass
class BeliefUpdaterConfig:
    """信念更新配置"""
    belief_inertia: float = 0.6          # α：旧信念保留度
    narrative_weight: float = 0.15       # β：叙事影响权重
    price_confirmation_weight: float = 0.2  # γ：价格确认效应
    social_pressure_weight: float = 0.1  # δ：社会压力（羊群）
    contradiction_penalty: float = 0.1   # θ：叙事证伪惩罚
    max_belief_change: float = 0.3       # 单步最大变化量


class BeliefUpdaterV2:
    """
    V0.2 信念更新引擎。

    将叙事曝光和KOL网络状态纳入信念更新。
    """

    def __init__(self, config: Optional[BeliefUpdaterConfig] = None):
        self.config = config or BeliefUpdaterConfig()

    def update_all(self,
                   agents: List[BaseAgent],
                   market: MarketEnvironment,
                   emotion: EmotionField,
                   kol_network: Optional[KOLNetwork] = None,
                   narrative_engine: Optional[NarrativeEngine] = None,
                   social_pressure_override: float = 0.0):
        """
        更新所有Agent的信念。

        参数：
        - kol_network：KOL网络，提供社会压力和叙事曝光
        - narrative_engine：叙事引擎，提供叙事推动力
        - social_pressure_override：直接传入的社会压力（羊群压力）
        """
        price_change = market.price_change_pct if market.price_history else 0.0

        # 价格确认效应：价格变动本身验证/否定叙事
        price_confirmation = self._compute_price_confirmation(price_change)

        # 社会压力：使用KOL网络或直接传入
        social_pressure = social_pressure_override
        if kol_network is not None:
            stats = kol_network.belief_statistics()
            social_pressure = stats["mean_belief"]  # KOL网络整体信念方向

        # 叙事总推动力
        narrative_shift = 0.0
        if narrative_engine is not None:
            narrative_shift = narrative_engine.aggregate_belief_shift(price_confirmation)

        # 叙事证伪信号：价格上涨但叙事是负向，或反之
        contradiction_signal = self._compute_contradiction(
            price_change, narrative_engine, emotion
        )

        for agent in agents:
            self._update_single(
                agent,
                price_confirmation=price_confirmation,
                social_pressure=social_pressure,
                narrative_shift=narrative_shift,
                contradiction_signal=contradiction_signal,
            )

    def _update_single(self,
                       agent: BaseAgent,
                       price_confirmation: float,
                       social_pressure: float,
                       narrative_shift: float,
                       contradiction_signal: float):
        """更新单个Agent的信念"""
        old_belief = agent.belief

        # Agent特定的权重（情绪化散户更受叙事影响，价值投资者更看价格）
        cfg = self.config
        sens = agent.config.emotional_sensitivity
        alpha = cfg.belief_inertia * (1.0 - sens * 0.2)
        beta = cfg.narrative_weight * sens
        gamma = cfg.price_confirmation_weight * (1.0 - sens * 0.3)

        delta = cfg.social_pressure_weight * agent.config.herding_coefficient
        theta = cfg.contradiction_penalty * agent.config.confirmation_bias

        belief_change = (
            alpha * old_belief
            + beta * narrative_shift
            + gamma * price_confirmation
            + delta * social_pressure
            - theta * contradiction_signal
        )

        # 约束单步最大变化
        delta_actual = np.clip(
            belief_change - old_belief,
            -cfg.max_belief_change,
            cfg.max_belief_change
        )
        agent.belief = np.clip(old_belief + delta_actual, -1.0, 1.0)

    def _compute_price_confirmation(self, price_change_pct: float) -> float:
        """
        价格确认效应。
        上涨 = 叙事被验证 = 信念向积极方向移动
        下跌 = 叙事被否定 = 信念向消极方向移动
        """
        return np.clip(price_change_pct * self.config.price_confirmation_weight * 2,
                       -0.5, 0.5)

    def _compute_contradiction(self,
                                price_change_pct: float,
                                narrative_engine: Optional[NarrativeEngine],
                                emotion: EmotionField) -> float:
        """
        叙事证伪信号。
        当价格变动与叙事方向矛盾时，触发惩罚。

        例：正向叙事（利好）出现，但价格下跌 → 矛盾信号
        """
        if narrative_engine is None:
            return 0.0

        # 简单判断：情绪场整体方向 vs 实际价格方向
        emotion_direction = emotion.fear_greed_index  # 正=贪婪主导，负=恐惧主导
        price_direction = np.sign(price_change_pct) if abs(price_change_pct) > 0.005 else 0

        if price_direction != 0 and price_direction != np.sign(emotion_direction):
            # 方向矛盾
            contradiction_strength = abs(price_change_pct) * self.config.contradiction_penalty * 2
            return float(contradiction_strength)

        return 0.0


def compute_market_belief_centrality(agents: List[BaseAgent]) -> float:
    """
    市场信念集中度。
    值越高 = 市场共识越强（泡沫/恐慌形成条件）
    值越低 = 分散（正常市场）
    """
    if not agents:
        return 0.0
    beliefs = [a.belief for a in agents]
    # 用平均绝对值作为集中度指标
    return float(np.mean([abs(b) for b in beliefs]))


def detect_reflexivity_regime(price_change_pct: float,
                                belief_concentration: float,
                                emotion_amplification: float) -> str:
    """
    识别当前反身性 regime。

    - bubble：信念高度集中 + 价格持续上涨
    - crash：信念高度集中 + 价格持续下跌
    - normal：低信念集中
    - transition：过渡状态
    """
    if belief_concentration > 0.6:
        if price_change_pct > 0.02:
            return "bubble"
        elif price_change_pct < -0.02:
            return "crash"
        elif emotion_amplification > 0.5:
            return "panic_spread"
    elif belief_concentration > 0.3:
        if abs(price_change_pct) > 0.01:
            return "transition"
    return "normal"
