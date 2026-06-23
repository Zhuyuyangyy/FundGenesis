"""
core/scenario_config.py
========================
P1.4: YAML 驱动的场景配置。

用 YAML / JSON 驱动实验，而不是写死 Python demo。

示例 YAML：
  id: A01
  name: positive_narrative_bubble
  steps: 200
  seed: 42

  market:
    initial_price: 100
    impact_coefficient: 0.5
    noise_std: 0.008

  narratives:
    - step: 30
      type: positive_growth
      strength: 0.75
      credibility: 0.70

  regulation:
    mode: none  # none / light / strong

  expected:
    price_peak_min: 160
    bubble_risk_peak_min: 0.15
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import os


@dataclass
class NarrativeInjection:
    """叙事注入配置"""
    step: int
    name: str = ""
    category: str = "fintech"
    polarity: str = "positive"
    intensity: float = 0.7
    credibility: float = 0.6
    target_sector: str = ""


@dataclass
class MarketConfig:
    """市场配置"""
    initial_price: float = 100.0
    impact_coefficient: float = 0.5
    noise_std: float = 0.008
    total_agents: int = 100


@dataclass
class EmotionConfig:
    """情绪配置"""
    initial_fear: float = 0.3
    initial_greed: float = 0.3
    initial_confidence: float = 0.5
    initial_uncertainty: float = 0.3
    inertia: float = 0.90


@dataclass
class KOLConfig:
    """KOL 网络配置"""
    n_macro: int = 3
    n_influencer: int = 8
    n_micro: int = 15
    n_retail: int = 100


@dataclass
class AgentConfig:
    """Agent 配置"""
    value_investor_ratio: float = 0.10
    trend_follower_ratio: float = 0.30
    emotional_retail_ratio: float = 0.60


@dataclass
class RegulationConfig:
    """监管配置"""
    mode: str = "none"  # none / light / strong
    force_strong_at_step: int = 30
    # 阈值
    monitor_threshold: float = 0.15
    human_review_threshold: float = 0.25
    block_threshold: float = 0.60


@dataclass
class ExpectedMetrics:
    """预期指标（用于验收）"""
    price_peak_min: Optional[float] = None
    price_peak_max: Optional[float] = None
    bubble_risk_peak_min: Optional[float] = None
    bubble_risk_peak_max: Optional[float] = None
    manipulation_risk_peak_min: Optional[float] = None
    high_risk_steps_min: Optional[int] = None
    high_risk_steps_max: Optional[int] = None
    narrative_penetration_min: Optional[float] = None


@dataclass
class ScenarioConfig:
    """
    P1.4: 完整场景配置。

    用 YAML 驱动实验，支持：
      - 市场参数
      - 情绪参数
      - KOL 网络参数
      - Agent 配置
      - 叙事注入计划
      - 监管配置
      - 预期指标（验收）
    """
    id: str = ""
    name: str = ""
    description: str = ""
    steps: int = 200
    seed: Optional[int] = None

    market: MarketConfig = field(default_factory=MarketConfig)
    emotion: EmotionConfig = field(default_factory=EmotionConfig)
    kol: KOLConfig = field(default_factory=KOLConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    regulation: RegulationConfig = field(default_factory=RegulationConfig)
    narratives: List[NarrativeInjection] = field(default_factory=list)
    expected: ExpectedMetrics = field(default_factory=ExpectedMetrics)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioConfig":
        """从字典创建配置"""
        market_data = data.get("market", {})
        emotion_data = data.get("emotion", {})
        kol_data = data.get("kol", {})
        agents_data = data.get("agents", {})
        reg_data = data.get("regulation", {})
        expected_data = data.get("expected", {})

        narratives = []
        for n in data.get("narratives", []):
            narratives.append(NarrativeInjection(
                step=n.get("step", 0),
                name=n.get("name", ""),
                category=n.get("category", "fintech"),
                polarity=n.get("polarity", "positive"),
                intensity=n.get("intensity", n.get("strength", 0.7)),
                credibility=n.get("credibility", 0.6),
                target_sector=n.get("target_sector", ""),
            ))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=data.get("steps", 200),
            seed=data.get("seed"),
            market=MarketConfig(**{k: v for k, v in market_data.items() if k in MarketConfig.__dataclass_fields__}),
            emotion=EmotionConfig(**{k: v for k, v in emotion_data.items() if k in EmotionConfig.__dataclass_fields__}),
            kol=KOLConfig(**{k: v for k, v in kol_data.items() if k in KOLConfig.__dataclass_fields__}),
            agents=AgentConfig(**{k: v for k, v in agents_data.items() if k in AgentConfig.__dataclass_fields__}),
            regulation=RegulationConfig(**{k: v for k, v in reg_data.items() if k in RegulationConfig.__dataclass_fields__}),
            narratives=narratives,
            expected=ExpectedMetrics(**{k: v for k, v in expected_data.items() if k in ExpectedMetrics.__dataclass_fields__}),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "ScenarioConfig":
        """从 YAML 文件加载配置"""
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        from dataclasses import asdict
        return asdict(self)

    def validate_results(self, results: Dict[str, Any]) -> Dict[str, bool]:
        """
        验证仿真结果是否符合预期指标。

        Returns:
            dict: {指标名: 是否通过}
        """
        checks = {}
        e = self.expected

        if e.price_peak_min is not None:
            checks["price_peak_min"] = results.get("price_peak", 0) >= e.price_peak_min
        if e.price_peak_max is not None:
            checks["price_peak_max"] = results.get("price_peak", 0) <= e.price_peak_max
        if e.bubble_risk_peak_min is not None:
            checks["bubble_risk_peak_min"] = results.get("peak_bubble_risk", 0) >= e.bubble_risk_peak_min
        if e.bubble_risk_peak_max is not None:
            checks["bubble_risk_peak_max"] = results.get("peak_bubble_risk", 0) <= e.bubble_risk_peak_max
        if e.manipulation_risk_peak_min is not None:
            checks["manipulation_risk_peak_min"] = results.get("peak_manipulation_risk", 0) >= e.manipulation_risk_peak_min
        if e.high_risk_steps_min is not None:
            checks["high_risk_steps_min"] = results.get("high_risk_steps", 0) >= e.high_risk_steps_min
        if e.high_risk_steps_max is not None:
            checks["high_risk_steps_max"] = results.get("high_risk_steps", 0) <= e.high_risk_steps_max

        return checks
