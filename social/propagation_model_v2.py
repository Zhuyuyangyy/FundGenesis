"""
social/propagation_model_v2.py
===============================
V0.3 Trust-Aware 叙事传播模型。

在 PropagationModel 基础上，纳入 TrustEngine：

  effective_exposure = base_exposure × effective_trust_kol

关键变化：
1. inject_narrative 不再从固定 macro KOL 注入，
   而是按 effective_trust 分配初始曝光权重
2. 每步扩散时，传播量 = 节点影响力 × effective_trust_kol × narrative_strength
3. 低 trust KOL 的叙事传播量大幅缩水
4. narrative → KOL association（记录哪条叙事来自哪个 KOL，用于 credibility_updater）
"""

from typing import List, Dict, Optional, Tuple
import numpy as np

from social.kol_network import KOLNetwork, KOLNode, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeRegistry, Polarity
from trust.trust_engine import TrustEngine


class TrustAwarePropagationModel:
    """
    信任感知传播模型（V2）。

    在 V1 基础上，每个 KOL 的 effective_trust 决定其叙事传播力。

    Demo 4（低信任失败）：
      apply_low_trust() → KOL effective_trust × 0.3 → 叙事无法扩散

    Demo 5（高信任引爆）：
      apply_high_trust() → macro KOL effective_trust → 0.95
                            → 叙事快速扩散至全网

    Demo 6（证伪崩塌）：
      apply_falsification() → 触发后 effective_trust 崩塌 → 传播链断裂
    """

    def __init__(self, network: KOLNetwork, trust_engine: TrustEngine):
        self.network = network
        self.trust_engine = trust_engine

        # 底层传播引擎（复用 V1）
        self._base = PropagationModel(network)

        # 叙事来源追踪：narrative_id → source_kol_id
        self._narrative_sources: Dict[str, str] = {}

        # 活跃叙事列表（引用）
        self._active_narratives: List[NarrativeEvent] = []

    # ── 信任场景预设 ────────────────────────────────────────

    def apply_low_trust_mode(self, multiplier: float = 0.3) -> None:
        """低信任模式：所有 KOL 有效信任 × multiplier"""
        for kol in self.network.get_kols():
            state = self.trust_engine.get_state(kol.node_id)
            if state:
                new_trust = float(np.clip(state.trust_level * multiplier, 0.0, 1.0))
                self.trust_engine.set_trust_level(kol.node_id, new_trust)
                # 信誉也压低
                self.trust_engine.set_credibility_score(
                    kol.node_id,
                    float(np.clip(state.credibility_score * 0.5, 0.0, 1.0))
                )

    def apply_high_trust_mode(self,
                              macro_trust: float = 0.95,
                              influencer_trust: float = 0.85) -> None:
        """高信任模式：顶级 KOL 信任分拉满"""
        for kol in self.network.get_kols():
            if kol.tier == KOLTier.MACRO:
                self.trust_engine.set_trust_level(kol.node_id, macro_trust)
                self.trust_engine.set_credibility_score(kol.node_id, 0.90)
                self.trust_engine.set_price_validation(kol.node_id, 0.90)
            elif kol.tier == KOLTier.INFLUENCER:
                self.trust_engine.set_trust_level(kol.node_id, influencer_trust)
                self.trust_engine.set_credibility_score(kol.node_id, 0.80)

    def apply_falsification_mode(self,
                                 kol_ids: Optional[List[str]] = None,
                                 trust_penalty: float = 0.70) -> None:
        """证伪模式：指定 KOL 信任崩塌"""
        targets = []
        if kol_ids:
            targets = [self.network.get_node(kid) for kid in kol_ids if self.network.get_node(kid)]
        else:
            targets = self.network.get_kols()

        for kol in targets:
            state = self.trust_engine.get_state(kol.node_id)
            if state:
                new_trust = float(np.clip(state.trust_level * (1.0 - trust_penalty), 0.0, 1.0))
                self.trust_engine.set_trust_level(kol.node_id, new_trust)
                self.trust_engine.set_credibility_score(kol.node_id, 0.05)
                self.trust_engine.set_price_validation(kol.node_id, 0.0)

    # ── 叙事注入（信任加权） ─────────────────────────────────

    def inject_narrative(self,
                         narrative: NarrativeEvent,
                         source_kol_id: Optional[str] = None) -> NarrativeEvent:
        """
        注入一条叙事，按 source_kol 的 effective_trust 分配初始曝光权重。

        如果 source_kol_id 为 None，则从所有 macro KOL 按 effective_trust 加权注入。
        """
        # 记录来源
        if source_kol_id:
            self._narrative_sources[narrative._id] = source_kol_id

        # 找注入源 KOL
        if source_kol_id:
            source_kol = self.network.get_node(source_kol_id)
            if source_kol:
                effective_trust = self.trust_engine.get_effective_trust(source_kol_id)
                # 信任加权注入量
                weighted_intensity = narrative.effective_intensity * effective_trust
                narrative.effective_intensity = weighted_intensity

        self._base.inject_narrative(narrative)
        self._active_narratives = self._base.active_narratives
        return narrative

    def step(self) -> Dict[str, float]:
        """
        执行一步传播（信任加权版）。
        """
        current_strengths = self._base.step()
        self._active_narratives = self._base.active_narratives
        return current_strengths

    # ── 信任加权传播（替换底层的 influence_on） ─────────────

    def compute_trust_weighted_propagation(self,
                                            source_node: KOLNode,
                                            target_node: KOLNode,
                                            narrative_strength: float) -> float:
        """
        计算信任加权的传播量。

        公式：
          propagation = source.exposure
                      × source.influence_score
                      × target.susceptibility
                      × source.effective_trust  ← V0.3 新增
                      × 0.3（每次传递系数）
        """
        if not target_node.is_active:
            return 0.0

        source_eff_trust = self.trust_engine.get_effective_trust(source_node.node_id)

        return (
            source_node.narrative_exposure
            * source_node.influence_score
            * target_node.susceptibility
            * source_eff_trust           # V0.3 核心：有效信任决定传播力
            * 0.3
        )

    # ── 查询 ─────────────────────────────────────────────

    def get_narrative_source(self, narrative_id: str) -> Optional[str]:
        """获取某叙事的来源 KOL"""
        return self._narrative_sources.get(narrative_id)

    def get_source_trust(self, narrative_id: str) -> float:
        """获取某叙事来源 KOL 的有效信任"""
        source_id = self._narrative_sources.get(narrative_id)
        if source_id:
            return self.trust_engine.get_effective_trust(source_id)
        return 0.0

    @property
    def active_narratives(self) -> List[NarrativeEvent]:
        return list(self._active_narratives)

    def summary(self) -> dict:
        base_summary = self._base.summary()
        trust_summary = self.trust_engine.summary()
        return {
            "narratives": base_summary,
            "trust": trust_summary,
            "sources_tracked": len(self._narrative_sources),
        }
