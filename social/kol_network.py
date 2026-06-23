"""
social/kol_network.py
=====================
KOL 社会传播图：建立舆论节点与普通投资者的图结构。

核心设计原则：
- 叙事不全局瞬时生效，而是沿图逐层扩散
- KOL节点有影响力、信任度，普通投资者有易感性
- 支持多层传播：KOL → 核心粉丝 → 二级粉丝 → 泛化用户
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import numpy as np
import uuid


class KOLTier(Enum):
    """KOL层级"""
    MACRO = "macro"           # 顶级媒体/机构
    INFLUENCER = "influencer"  # 中型KOL/大V
    MICRO = "micro"           # 小V/群主
    RETAIL = "retail"         # 普通投资者（最低影响力但数量最多）


@dataclass
class KOLNode:
    """
    图中的单个节点（可以是KOL或普通投资者）。

    P0.4 修复：belief_state 使用累积曝光 + tanh 激活 + 信念衰减，
    使社会传播可观测。
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tier: KOLTier = KOLTier.RETAIL
    name: str = ""

    # 影响力参数
    influence_score: float = 0.1      # [0, 1] 对他人的影响力
    trust_level: float = 0.5           # [0, 1] 自身被信任程度
    susceptibility: float = 0.6         # [0, 1] 对他人影响的敏感度
    confirmation_bias: float = 0.3     # [0, 1] 确认偏误程度
    risk_preference: float = 0.5        # [0, 1] 风险偏好

    # 状态
    belief_state: float = 0.0           # [-1, 1] 当前信念方向
    narrative_exposure: float = 0.0     # [0, 1] 当前叙事的曝光程度
    is_active: bool = True             # 节点是否活跃

    # P0.4: 累积曝光和信念衰减
    cumulative_exposure: float = 0.0    # 累积叙事曝光（非瞬时）
    exposure_gain: float = 2.0          # tanh 激活增益
    belief_decay: float = 0.95          # 信念自然衰减率
    max_belief_delta: float = 0.3       # 单步最大信念变化

    # 传播相关
    followers: List[str] = field(default_factory=list)
    following: List[str] = field(default_factory=list)

    @property
    def is_kol(self) -> bool:
        return self.tier != KOLTier.RETAIL

    def receive_exposure(self, exposure: float, source_trust: float = 1.0,
                         narrative_strength: float = 1.0):
        """
        P0.4: 接收叙事曝光，使用累积曝光 + tanh 激活 + 信任加权。

        公式：
          raw_exposure = exposure * source_trust * narrative_strength
          cumulative_exposure += raw_exposure
          belief_delta = tanh(exposure_gain * cumulative_exposure)
          belief_state = clip(belief_state * belief_decay + belief_delta, -1, 1)

        Args:
            exposure: 曝光强度 [0, 1]
            source_trust: 来源信任度 [0, 1]
            narrative_strength: 叙事强度 [0, 1]
        """
        # 1. 计算原始曝光（信任加权）
        raw_exposure = exposure * source_trust * narrative_strength
        self.cumulative_exposure += raw_exposure

        # 2. 更新瞬时曝光（用于传播模型兼容）
        self.narrative_exposure = np.clip(
            self.narrative_exposure + exposure * self.susceptibility,
            0.0, 1.0
        )

        # 3. tanh 激活：累积曝光 → 信念增量
        belief_delta = float(np.tanh(self.exposure_gain * self.cumulative_exposure))
        belief_delta = np.clip(belief_delta, -self.max_belief_delta, self.max_belief_delta)

        # 4. 信念衰减 + 增量
        self.belief_state = float(np.clip(
            self.belief_state * self.belief_decay + belief_delta,
            -1.0, 1.0
        ))

    def reset_exposure(self, decay: float = 0.1):
        """叙事曝光随时间衰减，同时衰减累积曝光"""
        self.narrative_exposure *= (1.0 - decay)
        # P0.4: 累积曝光也衰减（避免无限累积）
        self.cumulative_exposure *= (1.0 - decay * 0.5)

    def influence_on(self, target: "KOLNode", narrative_strength: float) -> float:
        """
        计算本节点对目标节点的叙事推动力。

        公式：
        influence = source.influence * target.susceptibility * narrative_strength * trust_level
        """
        if not target.is_active:
            return 0.0
        trust = target.trust_level  # 目标对任何来源的信任水平
        return (
            self.influence_score
            * target.susceptibility
            * narrative_strength
            * trust
        )

    def __repr__(self):
        return (f"KOLNode(id={self.node_id}, tier={self.tier.value}, "
                f"influence={self.influence_score:.2f}, "
                f"belief={self.belief_state:.2f}, "
                f"exposure={self.narrative_exposure:.2f})")


class KOLNetwork:
    """
    KOL社会传播网络。
    管理所有节点、边关系，支持叙事沿图扩散。
    """

    def __init__(self):
        self._nodes: Dict[str, KOLNode] = {}
        self._adjacency: Dict[str, Set[str]] = {}  # node_id -> set of neighbor node_ids

    def add_node(self, node: KOLNode) -> KOLNode:
        self._nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = set()
        return node

    def connect(self, follower_id: str, followee_id: str):
        """follower关注followee（信息从followee流向follower）"""
        if follower_id in self._nodes and followee_id in self._nodes:
            self._nodes[follower_id].following.append(followee_id)
            self._nodes[followee_id].followers.append(follower_id)
            self._adjacency[follower_id].add(followee_id)

    @property
    def nodes(self) -> List[KOLNode]:
        return list(self._nodes.values())

    def get_node(self, node_id: str) -> Optional[KOLNode]:
        return self._nodes.get(node_id)

    def get_kols(self) -> List[KOLNode]:
        return [n for n in self._nodes.values() if n.is_kol]

    def get_retail(self) -> List[KOLNode]:
        return [n for n in self._nodes.values() if n.tier == KOLTier.RETAIL]

    def reset_exposure_all(self, decay: float = 0.1):
        """重置所有节点的叙事曝光"""
        for node in self._nodes.values():
            node.reset_exposure(decay)

    def belief_statistics(self) -> dict:
        """市场信念统计"""
        beliefs = [n.belief_state for n in self._nodes.values()]
        exposures = [n.narrative_exposure for n in self._nodes.values()]
        if not beliefs:
            return {
                "mean_belief": 0.0,
                "belief_std": 0.0,
                "belief_concentration": 0.0,
                "mean_exposure": 0.0,
                "kol_count": len(self.get_kols()),
                "retail_count": len(self.get_retail()),
            }
        return {
            "mean_belief": float(np.mean(beliefs)),
            "belief_std": float(np.std(beliefs)),
            "belief_concentration": float(np.mean([abs(b) for b in beliefs])),
            "mean_exposure": float(np.mean(exposures)) if exposures else 0.0,
            "kol_count": len(self.get_kols()),
            "retail_count": len(self.get_retail()),
        }

    def build_default_network(self,
                               n_macro: int = 2,
                               n_influencer: int = 5,
                               n_micro: int = 10,
                               n_retail: int = 100) -> "KOLNetwork":
        """
        构建默认层级网络：

        Macro KOL
        ├── 所有 Influencer
        │   ├── 所有 Micro KOL
        │   │   └── 部分 Retail（核心粉丝）
        │   └── 部分 Retail
        ├── 部分 Influencer
        └── 部分 Retail

        形成"小世界网络"：大部分 Retail 只连接到自己层级的 Micro KOL。
        """
        # 创建节点
        kol_ids = {"macro": [], "influencer": [], "micro": [], "retail": []}

        for i in range(n_macro):
            node = KOLNode(
                tier=KOLTier.MACRO,
                name=f"MacroKOL_{i+1}",
                influence_score=np.random.uniform(0.8, 1.0),
                trust_level=np.random.uniform(0.7, 0.9),
                susceptibility=0.1,
                confirmation_bias=np.random.uniform(0.2, 0.4),
                # P0.4: Macro KOL 信念形成较慢（更理性），但需可观测
                exposure_gain=1.5,
                belief_decay=0.95,
                max_belief_delta=0.20,
            )
            kol_ids["macro"].append(self.add_node(node).node_id)

        for i in range(n_influencer):
            node = KOLNode(
                tier=KOLTier.INFLUENCER,
                name=f"Influencer_{i+1}",
                influence_score=np.random.uniform(0.4, 0.7),
                trust_level=np.random.uniform(0.5, 0.7),
                susceptibility=0.3,
                confirmation_bias=np.random.uniform(0.3, 0.6),
                # P0.4: Influencer 信念形成中等速度
                exposure_gain=1.8,
                belief_decay=0.93,
                max_belief_delta=0.25,
            )
            kol_ids["influencer"].append(self.add_node(node).node_id)

        for i in range(n_micro):
            node = KOLNode(
                tier=KOLTier.MICRO,
                name=f"MicroKOL_{i+1}",
                influence_score=np.random.uniform(0.15, 0.35),
                trust_level=np.random.uniform(0.3, 0.5),
                susceptibility=0.5,
                confirmation_bias=np.random.uniform(0.4, 0.7),
                # P0.4: Micro KOL 信念形成较快（更情绪化）
                exposure_gain=2.0,
                belief_decay=0.92,
                max_belief_delta=0.28,
            )
            kol_ids["micro"].append(self.add_node(node).node_id)

        for i in range(n_retail):
            node = KOLNode(
                tier=KOLTier.RETAIL,
                name=f"Investor_{i+1}",
                influence_score=np.random.uniform(0.01, 0.05),
                trust_level=np.random.uniform(0.3, 0.6),
                susceptibility=np.random.uniform(0.5, 0.8),
                confirmation_bias=np.random.uniform(0.3, 0.7),
                risk_preference=np.random.uniform(0.3, 0.8),
                # P0.4: Retail 信念形成最快（最情绪化）
                exposure_gain=2.5,
                belief_decay=0.90,
                max_belief_delta=0.30,
            )
            kol_ids["retail"].append(self.add_node(node).node_id)

        # 建边：Macro → Influencer → Micro → Retail
        # Macro 连接所有 Influencer
        for inf_id in kol_ids["influencer"]:
            for macro_id in kol_ids["macro"]:
                self.connect(inf_id, macro_id)

        # Influencer 连接 Macro + 部分 Influencer
        for i, inf_id in enumerate(kol_ids["influencer"]):
            for macro_id in kol_ids["macro"]:
                self.connect(inf_id, macro_id)
            for j, other_inf in enumerate(kol_ids["influencer"]):
                if i != j and np.random.random() < 0.3:
                    self.connect(inf_id, other_inf)

        # Micro 连接 Influencer + 部分其他 Micro
        for mic_id in kol_ids["micro"]:
            for inf_id in kol_ids["influencer"]:
                self.connect(mic_id, inf_id)
            if np.random.random() < 0.2:
                other_mic = np.random.choice(kol_ids["micro"])
                if other_mic != mic_id:
                    self.connect(mic_id, other_mic)

        # Retail：80%跟随自己的Micro，20%跟随Influencer
        for ret_id in kol_ids["retail"]:
            if np.random.random() < 0.8:
                # 跟随一个 Micro
                target_micro = np.random.choice(kol_ids["micro"])
                self.connect(ret_id, target_micro)
                # Micro 也可能被 Retail 跟随（已在上方建立）
            else:
                # 跟随 Influencer
                target_inf = np.random.choice(kol_ids["influencer"])
                self.connect(ret_id, target_inf)
            # 部分 Retail 跟随多个 Micro
            if np.random.random() < 0.3:
                extra_micro = np.random.choice(kol_ids["micro"])
                self.connect(ret_id, extra_micro)

        return self

    def __repr__(self):
        return f"KOLNetwork(nodes={len(self._nodes)}, kols={len(self.get_kols())})"
