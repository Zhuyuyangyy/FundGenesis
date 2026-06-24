"""
core/world_state.py
====================
P1.1: 统一世界状态对象。

所有模块状态收口到 WorldState，方便：
  - 保存快照
  - 回放
  - 测试
  - dashboard
  - 论文复现实验
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class MarketState:
    """市场状态快照"""
    price: float = 100.0
    initial_price: float = 100.0
    fundamental_value: float = 100.0
    step_net_demand: float = 0.0
    cumulative_net_demand: float = 0.0
    step_buy_volume: float = 0.0
    step_sell_volume: float = 0.0
    price_history: List[float] = field(default_factory=list)
    returns_history: List[float] = field(default_factory=list)
    reflexivity_index: float = 0.0
    volatility: float = 0.0

    @classmethod
    def from_market(cls, market) -> "MarketState":
        return cls(
            price=market.price,
            initial_price=market.initial_price,
            fundamental_value=market.fundamental_value,
            step_net_demand=market.step_net_demand,
            cumulative_net_demand=market.cumulative_net_demand,
            step_buy_volume=market.step_buy_volume,
            step_sell_volume=market.step_sell_volume,
            price_history=list(market.price_history),
            returns_history=list(market.returns_history),
            reflexivity_index=getattr(market, 'reflexivity_index', 0.0),
            volatility=getattr(market, 'volatility', 0.0),
        )


@dataclass
class EmotionState:
    """情绪场状态快照"""
    fear: float = 0.3
    greed: float = 0.3
    confidence: float = 0.5
    uncertainty: float = 0.3

    @classmethod
    def from_emotion(cls, emotion) -> "EmotionState":
        return cls(
            fear=emotion.fear,
            greed=emotion.greed,
            confidence=emotion.confidence,
            uncertainty=emotion.uncertainty,
        )


@dataclass
class NarrativeState:
    """单条叙事状态快照"""
    narrative_id: str
    name: str
    polarity: str
    intensity: float
    effective_intensity: float
    credibility: float
    age: int
    is_active: bool


@dataclass
class AgentState:
    """单个 Agent 状态快照"""
    agent_id: str
    agent_type: str
    belief_state: float
    position: float
    cash: float
    pnl: float
    trade_frequency: float
    fomo_sensitivity: float


@dataclass
class KOLNetworkState:
    """KOL 网络状态快照"""
    total_nodes: int
    total_kols: int
    tier_distribution: Dict[str, int] = field(default_factory=dict)
    mean_belief_by_tier: Dict[str, float] = field(default_factory=dict)
    mean_influence_by_tier: Dict[str, float] = field(default_factory=dict)
    mean_exposure_by_tier: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_network(cls, network) -> "KOLNetworkState":
        from social.kol_network import KOLTier
        tiers = {}
        belief_by_tier = {}
        influence_by_tier = {}
        exposure_by_tier = {}

        all_nodes = list(network.nodes)
        for node in all_nodes:
            tier_name = node.tier.value
            tiers[tier_name] = tiers.get(tier_name, 0) + 1
            belief_by_tier.setdefault(tier_name, []).append(node.belief_state)
            influence_by_tier.setdefault(tier_name, []).append(node.influence_score)
            exposure_by_tier.setdefault(tier_name, []).append(node.narrative_exposure)

        return cls(
            total_nodes=len(all_nodes),
            total_kols=len(network.get_kols()),
            tier_distribution=tiers,
            mean_belief_by_tier={k: float(np.mean(v)) for k, v in belief_by_tier.items()},
            mean_influence_by_tier={k: float(np.mean(v)) for k, v in influence_by_tier.items()},
            mean_exposure_by_tier={k: float(np.mean(v)) for k, v in exposure_by_tier.items()},
        )


@dataclass
class RiskState:
    """风险状态快照"""
    manipulation_risk_score: float = 0.0
    risk_level: str = "low"
    kol_coordination_score: float = 0.0
    self_validation_score: float = 0.0
    fomo_score: float = 0.0
    trust_build_score: float = 0.0
    bubble_risk_score: float = 0.0
    panic_risk_score: float = 0.0
    reflexivity_index: float = 0.0

    @classmethod
    def from_reports(cls, risk_report, metrics) -> "RiskState":
        return cls(
            manipulation_risk_score=risk_report.manipulation_risk_score,
            risk_level=risk_report.risk_level.value if hasattr(risk_report.risk_level, 'value') else str(risk_report.risk_level),
            kol_coordination_score=risk_report.kol_coordination_score,
            self_validation_score=risk_report.self_validation_score,
            fomo_score=risk_report.fomo_score,
            trust_build_score=risk_report.trust_build_score,
            bubble_risk_score=metrics.bubble_risk_score,
            panic_risk_score=metrics.panic_risk_score,
            reflexivity_index=metrics.reflexivity_index,
        )


@dataclass
class InterventionRecord:
    """单步干预记录"""
    step: int
    actions: List[str]
    intensity: str
    risk_reduction: float = 0.0
    narrative_suppression: float = 0.0


@dataclass
class WorldState:
    """
    P1.1: 统一世界状态。

    收口所有模块状态，每个 step 结束时生成一份快照。
    """
    step: int = 0
    market: MarketState = field(default_factory=MarketState)
    emotion: EmotionState = field(default_factory=EmotionState)
    narratives: List[NarrativeState] = field(default_factory=list)
    agents: List[AgentState] = field(default_factory=list)
    kol_network: Optional[KOLNetworkState] = None
    risk: RiskState = field(default_factory=RiskState)
    interventions: List[InterventionRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的字典"""
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def snapshot(
        cls,
        step: int,
        market,
        emotion,
        narrative_engine,
        agents,
        kol_network,
        risk_report=None,
        metrics=None,
        interventions=None,
    ) -> "WorldState":
        """
        从当前各模块状态生成快照。

        Args:
            step: 当前步数
            market: MarketEnvironment
            emotion: EmotionField
            narrative_engine: NarrativeEngine
            agents: Agent 列表
            kol_network: KOLNetwork
            risk_report: ManipulationRiskReport (可选)
            metrics: ReflexivityMetrics (可选)
            interventions: 本步干预记录列表 (可选)
        """
        # 叙事状态
        narratives = []
        if narrative_engine is not None:
            for n in narrative_engine.registry.active:
                narratives.append(NarrativeState(
                    narrative_id=n._id,
                    name=n.name,
                    polarity=n.polarity.value if hasattr(n.polarity, 'value') else str(n.polarity),
                    intensity=n.intensity,
                    effective_intensity=n.effective_intensity,
                    credibility=n.credibility,
                    age=getattr(n, 'age', 0),
                    is_active=True,
                ))

        # Agent 状态
        agent_states = []
        for a in agents:
            agent_states.append(AgentState(
                agent_id=a.agent_id,
                agent_type=type(a).__name__,
                belief_state=getattr(a, 'belief_state', 0.0),
                position=getattr(a, 'position', 0.0),
                cash=getattr(a, 'cash', 0.0),
                pnl=getattr(a, 'pnl', 0.0),
                trade_frequency=getattr(a, 'trade_frequency', 1.0),
                fomo_sensitivity=getattr(a, 'fomo_sensitivity', 1.0),
            ))

        # 风险状态
        risk = RiskState()
        if risk_report is not None and metrics is not None:
            risk = RiskState.from_reports(risk_report, metrics)

        # 干预记录
        intervention_records = []
        if interventions:
            for iv in interventions:
                if hasattr(iv, 'actions'):
                    intervention_records.append(InterventionRecord(
                        step=step,
                        actions=iv.actions,
                        intensity=getattr(iv, 'intensity', 'unknown'),
                        risk_reduction=getattr(iv, 'risk_reduction', 0.0),
                        narrative_suppression=getattr(iv, 'narrative_suppression', 0.0),
                    ))

        return cls(
            step=step,
            market=MarketState.from_market(market),
            emotion=EmotionState.from_emotion(emotion),
            narratives=narratives,
            agents=agent_states,
            kol_network=KOLNetworkState.from_network(kol_network) if kol_network else None,
            risk=risk,
            interventions=intervention_records,
        )
