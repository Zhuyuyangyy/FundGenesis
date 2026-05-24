"""
narrative/narrative_engine.py
===============================
NarrativeEngine：将叙事事件转换为市场心理状态变化。

关键原则（反身性约束）：
  叙事不能直接改价格，必须经过：
  Narrative → Belief Shift → Emotion Update → Behavior Change → Capital Flow → Price Change
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np

from narrative.narrative_event import NarrativeEvent, NarrativeRegistry, Polarity
from core.emotion_field import EmotionField


@dataclass
class NarrativeEngineConfig:
    """叙事引擎配置"""
    # 叙事对信念的影响系数
    belief_impact_coef: float = 0.3
    # 叙事对情绪的影响系数（慢于信念）
    emotion_impact_coef: float = 0.15
    # 新叙事触发更新的速度（novelty越高越快）
    novelty_boost: float = 0.2
    # 叙事衰减速度
    decay_rate: float = 0.05
    # 价格确认效应：价格变动反向强化叙事信念
    price_confirmation_boost: float = 0.25
    # 叙事冲突时的不确定性增幅
    narrative_conflict_uncertainty: float = 0.15


class NarrativeEngine:
    """
    叙事引擎：将叙事事件转化为信念/情绪变化。

    使用方法：
        engine = NarrativeEngine(config)
        engine.inject(narrative_event)
        engine.propagate_to_emotion(emotion_field, price_change_pct)
    """

    def __init__(self, config: Optional[NarrativeEngineConfig] = None):
        self.config = config or NarrativeEngineConfig()
        self.registry = NarrativeRegistry()
        self._belief_exposure: Dict[str, float] = {}   # narrative_id -> belief impact
        self._emotion_exposure: Dict[str, float] = {}  # narrative_id -> emotion impact
        # 监管干预降权因子：RegulatorAgent.narrative_throttle 写入，压制叙事强度
        self.narrative_strength_multiplier: float = 1.0

    def inject(self, event: NarrativeEvent) -> NarrativeEvent:
        """注入一条叙事事件"""
        self.registry.add(event)
        self._belief_exposure[event._id] = 0.0
        self._emotion_exposure[event._id] = 0.0
        return event

    def tick(self):
        """推进叙事衰减，返回过期叙事"""
        return self.registry.tick_all()

    def compute_belief_shift(self, narrative_id: str,
                               price_confirmation: float = 0.0) -> float:
        """
        计算单条叙事对信念的推动。

        参数：
        - price_confirmation: 价格变动率，正值=叙事被"验证"

        公式：
        belief_shift = intensity * credibility * novelty_boost
                     + price_confirmation * price_confirmation_boost
        """
        if narrative_id not in self._belief_exposure:
            return 0.0

        event = self._find_event(narrative_id)
        if event is None:
            return 0.0

        novelty_factor = 1.0 + self.config.novelty_boost * event.novelty
        confirmation_factor = 1.0 + self.config.price_confirmation_boost * price_confirmation

        shift = (
            event.effective_intensity
            * event.credibility
            * novelty_factor
            * confirmation_factor
            * self.config.belief_impact_coef
        )
        return float(np.clip(shift, -1.0, 1.0))

    def aggregate_belief_shift(self, price_confirmation: float = 0.0) -> float:
        """聚合所有活跃叙事的信念推动"""
        total = 0.0
        for nid in self._belief_exposure:
            total += self.compute_belief_shift(nid, price_confirmation)
        return float(np.clip(total, -1.0, 1.0))

    def propagate_to_emotion(self, emotion: EmotionField,
                               price_change_pct: float = 0.0,
                               narrative_conflict: bool = False):
        """
        将叙事影响传导到情绪场。

        关键约束：
        - 不直接修改价格
        - 情绪变化幅度 < 信念变化幅度（信念先变，情绪滞后）
        - 叙事冲突会增加不确定性
        """
        agg = self.registry.aggregate_impact()

        # 价格确认：若价格上涨，叙事被"验证"，强化贪婪
        if price_change_pct > 0:
            confirmation_bonus = price_change_pct * self.config.price_confirmation_boost
            agg["greed_delta"] += confirmation_bonus * 0.3
            agg["confidence_delta"] += confirmation_bonus * 0.2
        elif price_change_pct < 0:
            # 价格下跌被解读为叙事"证伪"
            rejection_penalty = abs(price_change_pct) * self.config.price_confirmation_boost
            agg["fear_delta"] += rejection_penalty * 0.2
            agg["uncertainty_delta"] += rejection_penalty * 0.2

        # 叙事冲突增加不确定性
        if narrative_conflict:
            agg["uncertainty_delta"] += self.config.narrative_conflict_uncertainty

        # 衰减已有情绪暴露
        for k in self._emotion_exposure:
            self._emotion_exposure[k] *= (1.0 - self.config.decay_rate)

        # 更新情绪（使用影响系数，不能瞬变）
        coef = self.config.emotion_impact_coef
        emotion.greed = np.clip(
            emotion.greed + agg.get("greed_delta", 0.0) * coef, 0.0, 1.0)
        emotion.fear = np.clip(
            emotion.fear + agg.get("fear_delta", 0.0) * coef, 0.0, 1.0)
        emotion.confidence = np.clip(
            emotion.confidence + agg.get("confidence_delta", 0.0) * coef, 0.0, 1.0)
        emotion.uncertainty = np.clip(
            emotion.uncertainty + agg.get("uncertainty_delta", 0.0) * coef, 0.0, 1.0)

    def get_narrative_penetration(self, total_agents: int) -> float:
        """
        叙事渗透率：当前活跃叙事数量 / 总Agent数量。
        用于 reflexivity_monitor。
        """
        active_count = len(self.registry.active)
        return float(np.clip(active_count / max(total_agents, 1), 0.0, 1.0))

    def narrative_strength(self) -> float:
        """
        当前叙事总强度（强度加权），受监管干预压制。
        
        RegulatorAgent 的 narrative_throttle 动作通过写入
        narrative_strength_multiplier（< 1.0）来降低本值，
        从而降低 bubble_risk 中的 narrative_factor。
        """
        return sum(
            e.effective_intensity * e.credibility
            for e in self.registry.active
        ) * self.narrative_strength_multiplier

    def _find_event(self, narrative_id: str) -> Optional[NarrativeEvent]:
        for e in self.registry.active:
            if e._id == narrative_id:
                return e
        return None

    def summary(self) -> dict:
        """当前叙事状态摘要"""
        return {
            "active_count": len(self.registry),
            "total_strength": self.narrative_strength(),
            "active_narratives": [
                {
                    "id": e._id,
                    "name": e.name,
                    "polarity": e.polarity.value,
                    "effective_intensity": round(e.effective_intensity, 3),
                    "remaining_ratio": round(e.remaining_ratio, 3),
                }
                for e in self.registry.active
            ]
        }
