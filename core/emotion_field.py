"""
core/emotion_field.py
=====================
情绪场：fear / greed / confidence / uncertainty
"""

from dataclasses import dataclass, field
from typing import Optional


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass
class EmotionField:
    """
    市场情绪场状态向量。
    所有指数范围 [0, 1]，0=最低，1=最高。
    """
    fear: float = 0.3          # 恐慌指数
    greed: float = 0.3         # 贪婪指数
    confidence: float = 0.5   # 信心指数
    uncertainty: float = 0.3  # 不确定性指数
    fomo_pressure: float = 0.0  # FOMO 压力指数

    def normalize(self):
        self.fear = clamp(self.fear, 0.0, 1.0)
        self.greed = clamp(self.greed, 0.0, 1.0)
        self.confidence = clamp(self.confidence, 0.0, 1.0)
        self.uncertainty = clamp(self.uncertainty, 0.0, 1.0)
        self.fomo_pressure = clamp(self.fomo_pressure, 0.0, 1.0)

    def to_vector(self) -> list[float]:
        return [self.fear, self.greed, self.confidence, self.uncertainty, self.fomo_pressure]

    @property
    def fear_greed_index(self) -> float:
        """恐贪指数：greed - fear，范围 [-1, 1]"""
        return self.greed - self.fear

    def emotion_factor(self) -> float:
        """
        综合情绪因子，作为决策偏移项。
        范围大约 [-0.5, 0.5]
        """
        return (
            self.greed * 0.5
            - self.fear * 0.5
            + self.confidence * 0.1
            - self.uncertainty * 0.1
            + self.fomo_pressure * 0.3  # FOMO amplifies bullish sentiment
        )

    def apply_price_change(self, price_change_pct: float):
        """
        根据价格变动更新情绪。
        上涨 → 贪婪上升，恐惧下降
        下跌 → 恐惧上升，贪婪下降
        """
        if price_change_pct > 0:
            delta = price_change_pct
            self.greed = clamp(self.greed + delta * 0.5, 0.0, 1.0)
            self.fear = clamp(self.fear - delta * 0.3, 0.0, 1.0)
        else:
            delta = abs(price_change_pct)
            self.fear = clamp(self.fear + delta * 0.5, 0.0, 1.0)
            self.greed = clamp(self.greed - delta * 0.3, 0.0, 1.0)
        self.normalize()

    def apply_shock(self, shock_magnitude: float):
        """
        注入外部冲击。
        shock_magnitude > 0 → 利好 → 贪婪+
        shock_magnitude < 0 → 利空 → 恐惧+
        """
        if shock_magnitude > 0:
            self.greed = clamp(self.greed + shock_magnitude * 0.4, 0.0, 1.0)
            self.confidence = clamp(self.confidence + shock_magnitude * 0.2, 0.0, 1.0)
        else:
            self.fear = clamp(self.fear + abs(shock_magnitude) * 0.4, 0.0, 1.0)
            self.uncertainty = clamp(self.uncertainty + abs(shock_magnitude) * 0.3, 0.0, 1.0)
        self.normalize()

    def apply_fomo_signal(self, intensity: float, source: str = "risk_agent", decay: float = 0.85):
        """
        Apply FOMO signal from risk detection to emotion field.

        FOMO (Fear Of Missing Out) increases greed and creates fomo_pressure,
        which feeds back into agent decision-making through emotion_factor().

        Args:
            intensity: FOMO signal strength [0, 1]
            source: Source identifier for logging
            decay: Blending decay factor (higher = slower adaptation)
        """
        intensity = max(0.0, min(1.0, intensity))

        # Blend greed upward with FOMO intensity
        self.greed = clamp(self.greed * decay + intensity * (1.0 - decay), 0.0, 1.0)

        # Reduce fear when FOMO is strong (FOMO overrides caution)
        self.fear = clamp(self.fear * (1.0 - intensity * 0.3), 0.0, 1.0)

        # Increase confidence slightly (FOMO creates false confidence)
        self.confidence = clamp(
            self.confidence + intensity * 0.05, 0.0, 1.0
        )

        # Track FOMO pressure as a dedicated field
        self.fomo_pressure = clamp(
            getattr(self, 'fomo_pressure', 0.0) * 0.90 + intensity * 0.5,
            0.0, 1.0
        )

        self.normalize()

    def decay_toward_neutral(self, inertia: float = 0.95):
        """
        每步自然衰减向中性值回归（情绪不会永远持续）。
        inertia 越大，衰减越慢。
        """
        self.fear = clamp(self.fear * inertia + 0.3 * (1 - inertia), 0.0, 1.0)
        self.greed = clamp(self.greed * inertia + 0.3 * (1 - inertia), 0.0, 1.0)
        self.confidence = clamp(self.confidence * inertia + 0.5 * (1 - inertia), 0.0, 1.0)
        self.uncertainty = clamp(self.uncertainty * inertia + 0.3 * (1 - inertia), 0.0, 1.0)
        self.fomo_pressure = clamp(self.fomo_pressure * inertia + 0.0 * (1 - inertia), 0.0, 1.0)
        self.normalize()

    def copy(self) -> "EmotionField":
        return EmotionField(
            fear=self.fear,
            greed=self.greed,
            confidence=self.confidence,
            uncertainty=self.uncertainty,
            fomo_pressure=self.fomo_pressure,
        )

    def __repr__(self):
        return (f"EmotionField(fear={self.fear:.3f}, greed={self.greed:.3f}, "
                f"confidence={self.confidence:.3f}, uncertainty={self.uncertainty:.3f}, "
                f"fomo_pressure={self.fomo_pressure:.3f})")
