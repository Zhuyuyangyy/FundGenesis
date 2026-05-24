"""
core/creator_controller.py
============================
造物主控制层：配置市场参数、注入冲击、调度实验
"""

from dataclasses import dataclass, field
from typing import Optional, List
import json

from core.emotion_field import EmotionField
from core.market_environment import MarketEnvironment


@dataclass
class MarketConfig:
    """市场初始配置"""
    initial_price: float = 100.0
    initial_volatility: float = 0.02
    total_agents: int = 100
    transaction_cost: float = 0.001
    max_position: float = 1.0
    impact_coefficient: float = 0.15  # 降低以防止价格指数爆炸
    noise_std: float = 0.01


@dataclass
class ShockConfig:
    """外部冲击配置"""
    shock_type: Optional[str] = None   # "policy" / "news" / "black_swan"
    shock_magnitude: float = 0.0       # 正=利好，负=利空
    shock_timing: Optional[int] = None  # 第几步注入
    shock_description: str = ""


@dataclass
class CreatorController:
    """
    造物主控制层。
    控制市场初始状态、注入外部冲击、调节情绪场。
    """
    market_config: MarketConfig = field(default_factory=MarketConfig)
    emotion_config: dict = field(default_factory=lambda: {
        "initial_fear": 0.3,
        "initial_greed": 0.3,
        "fear_inertia": 0.95,
        "greed_inertia": 0.95,
    })
    shocks: List[ShockConfig] = field(default_factory=list)
    current_shock_idx: int = 0

    def reset(self):
        self.current_shock_idx = 0

    def setup_market(self) -> MarketEnvironment:
        """初始化市场环境"""
        market = MarketEnvironment()
        market.reset(
            initial_price=self.market_config.initial_price,
            impact_coefficient=self.market_config.impact_coefficient,
            noise_std=self.market_config.noise_std,
            total_agents=self.market_config.total_agents,
        )
        return market

    def setup_emotion(self) -> EmotionField:
        """初始化情绪场"""
        cfg = self.emotion_config
        emotion = EmotionField(
            fear=cfg.get("initial_fear", 0.3),
            greed=cfg.get("initial_greed", 0.3),
            confidence=0.5,
            uncertainty=0.3,
        )
        return emotion

    def check_and_inject_shock(self, step: int, market: MarketEnvironment,
                               emotion: EmotionField) -> Optional[ShockConfig]:
        """
        检查是否到达注入时机。
        返回注入的 ShockConfig（如果有），否则 None。
        """
        if self.current_shock_idx >= len(self.shocks):
            return None

        shock = self.shocks[self.current_shock_idx]
        if shock.shock_timing is not None and step >= shock.shock_timing:
            # 执行冲击
            market.apply_shock(shock.shock_magnitude)
            emotion.apply_shock(shock.shock_magnitude)
            self.current_shock_idx += 1
            return shock

        # 定时冲击（shock_timing None = 每步都检查类型）
        if shock.shock_timing is None and shock.shock_type is not None:
            return None  # 持续性冲击由外部处理

        return None

    def inject_shock_now(self, magnitude: float, market: MarketEnvironment,
                         emotion: EmotionField):
        """手动立即注入冲击"""
        emotion.apply_shock(magnitude)

    @staticmethod
    def from_dict(data: dict) -> "CreatorController":
        """从配置字典创建 CreatorController"""
        mc = MarketConfig(**data.get("market", {}))
        ec = data.get("emotion", {})
        shocks_raw = data.get("shocks", [])
        shocks = [ShockConfig(**s) if isinstance(s, dict) else s
                  for s in shocks_raw]
        return CreatorController(
            market_config=mc,
            emotion_config=ec,
            shocks=shocks,
        )

    def to_dict(self) -> dict:
        return {
            "market": self.market_config.__dict__,
            "emotion": self.emotion_config,
            "shocks": [
                {"shock_type": s.shock_type,
                 "shock_magnitude": s.shock_magnitude,
                 "shock_timing": s.shock_timing,
                 "shock_description": s.shock_description}
                for s in self.shocks
            ],
        }

    def save_config(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_config(path: str) -> "CreatorController":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CreatorController.from_dict(data)
