"""
social/propagation_model.py
============================
叙事沿KOL网络的传播模型。

核心原则：
- 叙事不全局瞬时生效
- 从KOL节点出发，逐层扩散到粉丝
- 每步传播要考虑：影响力 × 信任 × 叙事强度 × 节点易感性
"""

from typing import List, Dict, Optional
import numpy as np

from social.kol_network import KOLNetwork, KOLNode, KOLTier
from narrative.narrative_event import NarrativeEvent


class PropagationModel:
    """
    叙事传播模型。

    使用示例：
        propagator = PropagationModel(kol_network)
        propagator.inject_narrative(narrative_event)
        for step in range(100):
            propagator.step()
            # 检查 reflexivity_monitor
    """

    def __init__(self, network: KOLNetwork):
        self.network = network
        self._active_narratives: List[NarrativeEvent] = []
        # 每个叙事在每步对各节点的影响
        self._narrative_exposure: Dict[str, Dict[str, float]] = {}  # narrative_id -> {node_id: exposure}

    def inject_narrative(self, narrative: NarrativeEvent):
        """向网络注入一条叙事，从KOL源头开始"""
        self._active_narratives.append(narrative)
        nid = narrative._id
        self._narrative_exposure[nid] = {}

        # 叙事的初始注入点：找最顶级的KOL（macro层）
        # 叙事通过KOL发声，不是凭空出现
        macro_kols = [n for n in self.network.get_kols() if n.tier == KOLTier.MACRO]

        if macro_kols:
            # 按影响力分配初始曝光权重
            total_influence = sum(k.influence_score for k in macro_kols)
            if total_influence == 0:
                # Ablation case: all influence zeroed
                return
            for kol in macro_kols:
                exposure = narrative.effective_intensity * (kol.influence_score / total_influence)
                kol.receive_exposure(exposure)
                self._narrative_exposure[nid][kol.node_id] = exposure
        else:
            # 没有macro则从所有KOL开始
            kols = self.network.get_kols()
            if kols:
                total_influence = sum(k.influence_score for k in kols)
                for kol in kols:
                    exposure = narrative.effective_intensity * (kol.influence_score / total_influence)
                    kol.receive_exposure(exposure)
                    self._narrative_exposure[nid][kol.node_id] = exposure

    def step(self) -> Dict[str, float]:
        """
        执行一步传播：
        - 叙事从KOL向粉丝逐层扩散
        - 每个节点向其follower传递影响力

        返回：各叙事的当前传播强度 dict{narrative_id: strength}
        """
        # 更新叙事衰减
        expired = []
        for narrative in self._active_narratives:
            if not narrative.tick():
                expired.append(narrative)

        for narrative in expired:
            self._active_narratives.remove(narrative)

        # 叙事沿图扩散
        current_strengths = {}
        for narrative in self._active_narratives:
            nid = narrative._id
            current_strengths[nid] = 0.0
            narrative_exposure = self._narrative_exposure[nid]

            # 从所有KOL向其粉丝扩散
            for node in self.network.nodes:
                if node.narrative_exposure <= 0.01:
                    continue

                # 节点向每个follower传递影响力
                for follower_id in node.followers:
                    follower = self.network.get_node(follower_id)
                    if follower is None:
                        continue

                    # 传播量 = 节点影响力 × 叙事强度 × (1 - 距离衰减)
                    # 这里简化为：节点已接收的exposure × influence × susceptibility
                    propagation = (
                        node.narrative_exposure
                        * node.influence_score
                        * follower.susceptibility
                        * 0.3  # 每次传播只传递30%，避免瞬间全覆盖
                    )

                    follower.receive_exposure(propagation)
                    narrative_exposure[follower_id] = (
                        narrative_exposure.get(follower_id, 0.0) + propagation
                    )

            # 叙事曝光衰减
            self.network.reset_exposure_all(decay=0.08)
            current_strengths[nid] = narrative.effective_intensity

        return current_strengths

    def get_node_exposure(self, narrative_id: str) -> List[float]:
        """获取某叙事在各节点的曝光分布"""
        if narrative_id not in self._narrative_exposure:
            return []
        return list(self._narrative_exposure[narrative_id].values())

    def get_network_exposure(self, narrative_id: str) -> float:
        """网络总曝光量"""
        if narrative_id not in self._narrative_exposure:
            return 0.0
        return sum(self._narrative_exposure[narrative_id].values())

    def get_tier_exposure(self, narrative_id: str) -> dict:
        """各层级的平均曝光"""
        if narrative_id not in self._narrative_exposure:
            return {}
        result = {}
        for tier in KOLTier:
            nodes = [n for n in self.network.nodes if n.tier == tier]
            if nodes:
                exposures = [
                    self._narrative_exposure[narrative_id].get(n.node_id, 0.0)
                    for n in nodes
                ]
                result[tier.value] = float(np.mean(exposures))
        return result

    @property
    def active_narratives(self) -> List[NarrativeEvent]:
        return list(self._active_narratives)

    def summary(self) -> dict:
        return {
            "active_count": len(self._active_narratives),
            "active_narratives": [
                {
                    "id": n._id,
                    "name": n.name,
                    "polarity": n.polarity.value,
                    "strength": round(n.effective_intensity, 4),
                }
                for n in self._active_narratives
            ]
        }
