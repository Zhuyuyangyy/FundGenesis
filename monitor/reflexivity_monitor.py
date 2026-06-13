"""
monitor/reflexivity_monitor.py
===============================
Reflexivity Monitor：实时监控泡沫风险与反身性强度。

核心指标：
- Narrative Penetration：叙事传播覆盖率
- Belief Concentration：市场信念一致性
- Emotion Amplification：情绪放大倍数
- Capital Imbalance：买卖资金失衡
- Reflexivity Index：综合反身性强度
- Bubble Risk Score：泡沫风险分数
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import logging
import numpy as np

from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from social.kol_network import KOLNetwork
from narrative.narrative_engine import NarrativeEngine

logger = logging.getLogger('FundGenesis.monitor')


class MarketRegime(Enum):
    NORMAL = "normal"
    BUBBLE_FORMING = "bubble_forming"
    BUBBLE_PEAK = "bubble_peak"
    CRASH = "crash"
    PANIC_SPREAD = "panic_spread"
    RECOVERY = "recovery"


@dataclass
class ReflexivityMetrics:
    """单步反身性指标快照"""
    step: int

    # 叙事层
    narrative_penetration: float = 0.0      # [0,1] 叙事渗透率
    narrative_strength: float = 0.0         # 叙事总强度
    active_narrative_count: int = 0

    # 信念层
    belief_concentration: float = 0.0        # [0,1] 信念一致性
    belief_centrality: float = 0.0          # [-1,1] 整体方向

    # 情绪层
    fear_level: float = 0.0
    greed_level: float = 0.0
    emotion_amplification: float = 0.0     # 情绪极端程度
    fear_greed_index: float = 0.0           # [-1,1]

    # 资金流
    capital_imbalance: float = 0.0          # [-1,1] net资金流方向
    volatility: float = 0.0

    # 价格层
    price_change_pct: float = 0.0
    price_level: float = 0.0

    # 综合指标
    reflexivity_index: float = 0.0          # [0,1] 综合反身性强度
    bubble_risk_score: float = 0.0           # [0,1] 泡沫风险
    panic_risk_score: float = 0.0            # [0,1] 恐慌风险

    # Regime
    regime: MarketRegime = MarketRegime.NORMAL

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "narrative_penetration": round(self.narrative_penetration, 4),
            "narrative_strength": round(self.narrative_strength, 4),
            "belief_concentration": round(self.belief_concentration, 4),
            "belief_centrality": round(self.belief_centrality, 4),
            "emotion_amplification": round(self.emotion_amplification, 4),
            "fear_greed_index": round(self.fear_greed_index, 4),
            "capital_imbalance": round(self.capital_imbalance, 4),
            "volatility": round(self.volatility, 4),
            "price_change_pct": round(self.price_change_pct, 4),
            "reflexivity_index": round(self.reflexivity_index, 4),
            "bubble_risk_score": round(self.bubble_risk_score, 4),
            "panic_risk_score": round(self.panic_risk_score, 4),
            "regime": self.regime.value,
        }


class ReflexivityMonitor:
    """
    反身性监控器。

    使用方法：
        monitor = ReflexivityMonitor()
        for step in range(1000):
            metrics = monitor.observe(
                step=step,
                market=market,
                emotion=emotion,
                kol_network=kol_network,
                narrative_engine=narrative_engine,
                agents=agents,
            )
            if metrics.bubble_risk_score > 0.7:
                logger.warning("ALERT: Bubble risk detected!")
    """

    # 指标权重（用于计算 reflexivity_index）
    WEIGHTS = {
        "narrative_penetration": 0.15,
        "belief_concentration": 0.20,
        "emotion_amplification": 0.20,
        "capital_imbalance": 0.25,
        "price_momentum": 0.20,
    }

    def __init__(self):
        self._history: List[ReflexivityMetrics] = []
        self._regime_persistence: Dict[MarketRegime, int] = {
            r: 0 for r in MarketRegime
        }

    def observe(self,
                step: int,
                market: MarketEnvironment,
                emotion: EmotionField,
                kol_network: Optional[KOLNetwork],
                narrative_engine: Optional[NarrativeEngine],
                agents: List,          # BaseAgent list
                ) -> ReflexivityMetrics:
        """
        执行一次观测，返回当前步的指标快照。
        """
        # --- 叙事层 ---
        if narrative_engine is not None:
            narrative_strength = narrative_engine.narrative_strength()
            narrative_penetration = (
                narrative_engine.get_narrative_penetration(len(agents))
                if agents else 0.0
            )
            active_count = len(narrative_engine.registry.active)
        else:
            narrative_strength = 0.0
            narrative_penetration = 0.0
            active_count = 0

        # --- 信念层 ---
        if kol_network is not None:
            stats = kol_network.belief_statistics()
            belief_concentration = stats["belief_concentration"]
            belief_centrality = stats["mean_belief"]
        elif agents:
            beliefs = [getattr(a, 'belief', 0.0) for a in agents]
            belief_concentration = float(np.mean([abs(b) for b in beliefs]))
            belief_centrality = float(np.mean(beliefs))
        else:
            belief_concentration = 0.0
            belief_centrality = 0.0

        # --- 情绪层 ---
        fear_level = emotion.fear
        greed_level = emotion.greed
        fear_greed_index = emotion.fear_greed_index

        # 情绪放大：fear和greed同时高 = 极端分化
        emotion_amplification = float(
            np.clip(abs(fear_greed_index) + abs(fear_level - greed_level) * 0.3,
                    0.0, 1.0)
        )

        # --- 资金流 ---
        capital_imbalance = market.net_demand / max(market.total_agents, 1) if hasattr(market, 'net_demand') else 0.0

        # --- 价格层 ---
        price_change_pct = market.price_change_pct if market.price_history else 0.0
        price_level = market.price if hasattr(market, 'price') else 0.0
        volatility = market.volatility if hasattr(market, 'volatility') else 0.0

        # --- 综合指标 ---
        price_momentum = float(np.clip(abs(price_change_pct) * 5, 0.0, 1.0))

        reflexivity_index = (
            self.WEIGHTS["narrative_penetration"] * narrative_penetration
            + self.WEIGHTS["belief_concentration"] * belief_concentration
            + self.WEIGHTS["emotion_amplification"] * emotion_amplification
            + self.WEIGHTS["capital_imbalance"] * min(abs(capital_imbalance), 1.0)
            + self.WEIGHTS["price_momentum"] * price_momentum
        )

        # --- 泡沫/恐慌风险 ---
        bubble_risk_score = self._compute_bubble_risk(
            belief_concentration, emotion_amplification,
            price_change_pct, narrative_strength, capital_imbalance,
            volatility=volatility
        )
        panic_risk_score = self._compute_panic_risk(
            fear_level, emotion_amplification, price_change_pct,
            belief_concentration
        )

        # --- Regime 检测 ---
        regime = self._detect_regime(
            reflexivity_index=reflexivity_index,
            belief_concentration=belief_concentration,
            fear_greed_index=fear_greed_index,
            price_change_pct=price_change_pct,
            emotion_amplification=emotion_amplification,
        )

        metrics = ReflexivityMetrics(
            step=step,
            narrative_penetration=narrative_penetration,
            narrative_strength=narrative_strength,
            active_narrative_count=active_count,
            belief_concentration=belief_concentration,
            belief_centrality=belief_centrality,
            fear_level=fear_level,
            greed_level=greed_level,
            emotion_amplification=emotion_amplification,
            fear_greed_index=fear_greed_index,
            capital_imbalance=capital_imbalance,
            volatility=volatility,
            price_change_pct=price_change_pct,
            price_level=price_level,
            reflexivity_index=reflexivity_index,
            bubble_risk_score=bubble_risk_score,
            panic_risk_score=panic_risk_score,
            regime=regime,
        )

        self._history.append(metrics)
        return metrics

    def _compute_bubble_risk(self,
                              belief_concentration: float,
                              emotion_amplification: float,
                              price_change_pct: float,
                              narrative_strength: float,
                              capital_imbalance: float,
                              volatility: float = 0.0) -> float:
        """
        泡沫风险 = 信念集中 × 情绪放大 × 波动率 regime × 资金流入 × 叙事强度

        用波动率替代单步价格变化率：波动率是regime指标，捕捉持续高波动（泡沫特征）
        而单步价格变化率是moment-to-moment指标，对泡沫检测不够稳定
        """
        # 波动率作为价格动量的基础（regime级别，不受单步噪声影响）
        # normal=0.013→0.65，bubble=0.07→1.0，捕捉持续高波动
        # 50x系数（原10x→50x）：让波动率在泡沫期充分主导bubble_risk
        volatility_momentum = float(np.clip(volatility * 50, 0.0, 1.0))
        # 叙事强度因子（受 narrative_throttle 干预影响）
        narrative_factor = min(narrative_strength / 2.0, 1.0)

        # 信念集中度：KOL belief修复后从 ~0.004 → 0.04，belief_boost 从 0.1 → 1.0
        belief_boost = belief_concentration * 30.0
        # 情绪放大系数
        emotion_boost = emotion_amplification * 4.0
        # 资金流入归一化：使用 sqrt 缩放避免 ci=0 时彻底杀风险
        # ci=0 → cap=0.1（最小基线，允许其他因子主导风险）
        # ci=5 → cap=1.0（最大归一化）
        # ci=1 → cap=0.1 + 0.9*0.2 = 0.28（资金流入明显时放大风险）
        capital_factor = 0.1 + 0.9 * min(abs(capital_imbalance) / 5.0, 1.0)

        # 整体系数 1.0（原 500→3.5→1.0），防止过饱和到 1.0
        # 典型泡沫期（bc=0.04, ea=0.53, vm=0.70）:
        #   无干预：1.2*2.12*0.70*1.0*0.8*0.875 ≈ 0.874（接近上限但不过饱和）
        #   Strong（narrative_throttle 压至 0.48）: 1.2*2.12*0.70*1.0*0.8*0.740 ≈ 0.739
        #   Light（narrative_throttle 压至 0.60）: 1.2*2.12*0.70*1.0*0.8*0.800 ≈ 0.799
        # 干预效果传导路径：RegulatorAgent._apply_to_narrative_engine() 
        #   → engine.narrative_strength_multiplier 降低
        #   → NarrativeEngine.narrative_strength() 返回值下降
        #   → _compute_bubble_risk 的 narrative_strength 参数下降
        #   → narrative_factor = ns/2 下降
        #   → bubble_risk 公式中 narrative_factor 项下降
        #   → Strong < Light < Baseline 排序成立
        k = 1.0
        risk = (
            belief_boost
            * emotion_boost
            * volatility_momentum
            * k
            * capital_factor
            * (0.5 + 0.5 * narrative_factor)
        )
        return float(np.clip(risk, 0.0, 1.0))

    def _compute_panic_risk(self,
                             fear_level: float,
                             emotion_amplification: float,
                             price_change_pct: float,
                             belief_concentration: float) -> float:
        """
        恐慌风险 = 恐惧 × 情绪放大 × 价格下跌动量 × 信念集中
        """
        price_down_momentum = max(0.0, -price_change_pct)

        risk = (
            fear_level
            * emotion_amplification
            * price_down_momentum * 5
            * (0.5 + 0.5 * belief_concentration)
        )
        return float(np.clip(risk, 0.0, 1.0))

    def _detect_regime(self,
                        reflexivity_index: float,
                        belief_concentration: float,
                        fear_greed_index: float,
                        price_change_pct: float,
                        emotion_amplification: float) -> MarketRegime:
        """检测市场 Regime"""
        # 更新 regime 持续计数
        if reflexivity_index > 0.7 and belief_concentration > 0.6:
            if price_change_pct > 0.01:
                self._regime_persistence[MarketRegime.BUBBLE_FORMING] += 1
                self._regime_persistence[MarketRegime.CRASH] = 0
                if self._regime_persistence[MarketRegime.BUBBLE_FORMING] > 10:
                    return MarketRegime.BUBBLE_PEAK
                return MarketRegime.BUBBLE_FORMING
            elif price_change_pct < -0.01:
                self._regime_persistence[MarketRegime.CRASH] += 1
                self._regime_persistence[MarketRegime.BUBBLE_FORMING] = 0
                return MarketRegime.CRASH
        elif emotion_amplification > 0.6 and fear_greed_index < -0.3:
            return MarketRegime.PANIC_SPREAD
        elif reflexivity_index < 0.3:
            for r in self._regime_persistence:
                self._regime_persistence[r] = 0
            return MarketRegime.NORMAL
        else:
            return MarketRegime.RECOVERY

        return MarketRegime.NORMAL

    @property
    def history(self) -> List[ReflexivityMetrics]:
        return list(self._history)

    def latest(self) -> Optional[ReflexivityMetrics]:
        return self._history[-1] if self._history else None

    def regime_summary(self) -> Dict[str, int]:
        """历史 Regime 分布"""
        counts = {}
        for m in self._history:
            r = m.regime.value
            counts[r] = counts.get(r, 0) + 1
        return counts

    def critical_steps(self, threshold: float = 0.7) -> List[ReflexivityMetrics]:
        """返回泡沫/恐慌风险超过阈值的步"""
        return [
            m for m in self._history
            if m.bubble_risk_score > threshold or m.panic_risk_score > threshold
        ]
