"""
narrative/narrative_event.py
=============================
NarrativeEvent 数据结构定义
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import uuid


class Polarity(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class NarrativeCategory(Enum):
    POLICY = "policy"                # 政策利好/利空
    SECTOR = "sector"                # 行业热点
    MACRO = "macro"                  # 宏观经济
    FINTECH = "fintech"              # 金融科技/AI叙事
    REGULATORY = "regulatory"        # 监管动态
    EARNINGS = "earnings"            # 业绩/数据
    MANIPULATION = "manipulation"    # 异常叙事（用于风险仿真）
    SENTIMENT = "sentiment"          # 市场情绪类


@dataclass
class NarrativeEvent:
    """
    叙事事件：一条在市场中传播的"故事"。

    与 ShockConfig 的本质区别：
    - ShockConfig：直接改价格/情绪（瞬时全局生效）
    - NarrativeEvent：通过KOL网络逐层扩散，先影响信念，再影响行为

    关键字段：
    - intensity: [0,1] 叙事强度，越高影响越大
    - credibility: [0,1] 叙事可信度，影响信念更新速度
    - novelty: [0,1] 叙事新颖度，全新叙事扩散更快
    - duration: 叙事有效步数
    - target_sector: 叙事聚焦板块，空字符串表示全局
    """
    name: str
    category: NarrativeCategory
    polarity: Polarity
    target_sector: str = ""              # "" = 全局叙事
    intensity: float = 0.5               # [0, 1]
    credibility: float = 0.6            # [0, 1]
    novelty: float = 0.5                 # [0, 1]
    duration: int = 20                  # 有效步数
    tags: List[str] = field(default_factory=list)
    source: str = "system"               # "system" / "KOL" / "media" / "regulator"
    _id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    _steps_remaining: int = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, '_steps_remaining', self.duration)

    def tick(self) -> bool:
        """每步调用，返回False表示叙事已过期"""
        if self._steps_remaining > 0:
            self._steps_remaining -= 1
            return True
        return False

    @property
    def is_active(self) -> bool:
        return self._steps_remaining > 0

    @property
    def remaining_ratio(self) -> float:
        """剩余强度比例，叙事随时间衰减"""
        if self.duration == 0:
            return 0.0
        return max(0.0, self._steps_remaining / self.duration)

    @property
    def effective_intensity(self) -> float:
        """衰减后的有效强度"""
        return self.intensity * self.remaining_ratio

    def to_impact(self) -> dict:
        """
        将叙事转换为心理影响因子。
        实际影响由 NarrativeEngine 调节，这里只做初始映射。
        """
        base = self.intensity * self.credibility * (0.5 + 0.5 * self.novelty)

        if self.polarity == Polarity.POSITIVE:
            return {
                "greed_delta": base * 0.4,
                "confidence_delta": base * 0.3,
                "uncertainty_delta": -base * 0.1,
                "fear_delta": -base * 0.1,
                "risk_appetite_delta": base * 0.3,
            }
        elif self.polarity == Polarity.NEGATIVE:
            return {
                "fear_delta": base * 0.4,
                "uncertainty_delta": base * 0.3,
                "greed_delta": -base * 0.2,
                "confidence_delta": -base * 0.2,
                "risk_appetite_delta": -base * 0.3,
            }
        else:
            return {
                "uncertainty_delta": base * 0.2,
                "confidence_delta": -base * 0.1,
            }

    def __repr__(self):
        return (f"NarrativeEvent(id={self._id}, name={self.name}, "
                f"polarity={self.polarity.value}, intensity={self.intensity:.2f}, "
                f"remaining={self._steps_remaining})")


class NarrativeRegistry:
    """
    叙事事件管理器：追踪当前活跃叙事。
    """
    def __init__(self):
        self._active: List[NarrativeEvent] = []

    def add(self, event: NarrativeEvent):
        self._active.append(event)

    def tick_all(self):
        """推进所有叙事，返回已过期的叙事列表"""
        expired = []
        remaining = []
        for e in self._active:
            if e.tick():
                remaining.append(e)
            else:
                expired.append(e)
        self._active = remaining
        return expired

    @property
    def active(self) -> List[NarrativeEvent]:
        return list(self._active)

    def active_by_category(self, cat: NarrativeCategory) -> List[NarrativeEvent]:
        return [e for e in self._active if e.category == cat]

    def aggregate_impact(self) -> dict:
        """
        聚合所有活跃叙事产生的情绪影响。
        """
        total = {
            "greed_delta": 0.0,
            "confidence_delta": 0.0,
            "uncertainty_delta": 0.0,
            "fear_delta": 0.0,
            "risk_appetite_delta": 0.0,
        }
        for e in self._active:
            imp = e.to_impact()
            for k in total:
                total[k] += imp.get(k, 0.0) * e.remaining_ratio
        return total

    def __len__(self):
        return len(self._active)
