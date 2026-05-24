"""
trust/trust_engine.py
=====================
V0.3 核心：动态信任引擎。

TrustEngine 负责：
1. 持有每个 KOL 的 trust_level + credibility_score
2. 计算"有效信任"（Trust × Credibility × SocialProof × PriceValidation）
3. 提供传播时的 trust_weight

核心公式：
  effective_trust = T_kol × C_kol^α × S_kol^β × V_kol^γ

其中：
  T_kol ∈ [0, 1]  — 信任基础分（来自bootstrapper）
  C_kol ∈ [0, 1]  — 信誉分（来自 credibility_updater，历史预测准确率）
  S_kol          — 社会证明（追随者数量归一化）
  V_kol ∈ [0, 1]  — 价格验证系数（最近 N 步价格是否验证了该 KOL 的叙事）
"""

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class TrustConfig:
    """信任引擎配置"""
    credibility_alpha: float = 0.6      # α：Credibility 在有效信任中的指数
    social_proof_beta: float = 0.3     # β：SocialProof 的指数
    price_validation_gamma: float = 0.4 # γ：PriceValidation 的指数
    min_effective_trust: float = 0.01  # 最低有效信任（防止归零）


class KOLTrustState:
    """单个 KOL 的信任状态快照（使用 __slots__ 避免 dataclass config 问题）"""
    __slots__ = ('kol_id', 'trust_level', 'credibility_score',
                 'social_proof', 'price_validation', 'last_update_step',
                 '_config_ref')

    def __init__(self, kol_id: str, trust_level: float, credibility_score: float,
                 social_proof: float, price_validation: float,
                 last_update_step: int, config: TrustConfig):
        self.kol_id = kol_id
        self.trust_level = trust_level
        self.credibility_score = credibility_score
        self.social_proof = social_proof
        self.price_validation = price_validation
        self.last_update_step = last_update_step
        self._config_ref = config

    @property
    def effective_trust(self) -> float:
        """有效信任 = Trust × Credibility^α × SocialProof^β × PriceValidation^γ"""
        cfg = self._config_ref
        return float(np.clip(
            self.trust_level
            * (self.credibility_score ** cfg.credibility_alpha)
            * (self.social_proof ** cfg.social_proof_beta)
            * (self.price_validation ** cfg.price_validation_gamma),
            cfg.min_effective_trust,
            1.0
        ))


class TrustEngine:
    """
    全局信任引擎。
    管理所有 KOL 的动态信任状态。
    """

    def __init__(self, config: Optional[TrustConfig] = None):
        self.config = config or TrustConfig()
        self._states: Dict[str, KOLTrustState] = {}
        # 用于跟踪每个 KOL 追随者数量（用于社会证明）
        self._follower_counts: Dict[str, int] = {}

    # ── 基本操作 ──────────────────────────────────────────

    def init_kol(self, kol_id: str, initial_trust: float = 0.5) -> KOLTrustState:
        """初始化一个 KOL 的信任状态"""
        if kol_id not in self._states:
            self._states[kol_id] = KOLTrustState(
                kol_id=kol_id,
                trust_level=initial_trust,
                credibility_score=0.5,
                social_proof=0.5,
                price_validation=0.5,
                last_update_step=0,
                config=self.config,
            )
        return self._states[kol_id]

    def get_state(self, kol_id: str) -> Optional[KOLTrustState]:
        """获取 KOL 信任状态"""
        return self._states.get(kol_id)

    def get_effective_trust(self, kol_id: str) -> float:
        """获取有效信任（传播时使用的核心权重）"""
        state = self._states.get(kol_id)
        if state is None:
            return 0.0
        return state.effective_trust

    def update_follower_counts(self, kol_network) -> None:
        """从 KOLNetwork 同步追随者数量，用于社会证明计算"""
        for kol in kol_network.get_kols():
            self._follower_counts[kol.node_id] = len(kol.followers)

        # 归一化社会证明
        if self._follower_counts:
            max_followers = max(self._follower_counts.values())
            if max_followers > 0:
                for kol_id in self._follower_counts:
                    raw = self._follower_counts[kol_id] / max_followers
                    if kol_id in self._states:
                        self._states[kol_id].social_proof = float(raw)

    # ── 直接更新（供 bootstrapper / updater 调用）───────────

    def set_trust_level(self, kol_id: str, value: float) -> None:
        """直接设置信任分（用于 bootstrapper 初始化）"""
        if kol_id in self._states:
            self._states[kol_id].trust_level = float(np.clip(value, 0.0, 1.0))

    def set_credibility_score(self, kol_id: str, value: float) -> None:
        """直接设置信誉分（用于 credibility_updater）"""
        if kol_id in self._states:
            self._states[kol_id].credibility_score = float(np.clip(value, 0.0, 1.0))

    def set_price_validation(self, kol_id: str, value: float) -> None:
        """直接设置价格验证系数（用于 credibility_updater）"""
        if kol_id in self._states:
            self._states[kol_id].price_validation = float(np.clip(value, 0.0, 1.0))

    def update_step(self, kol_id: str, step: int) -> None:
        """记录更新步数（用于 trust_decay_model）"""
        if kol_id in self._states:
            self._states[kol_id].last_update_step = step

    # ── 批量查询 ─────────────────────────────────────────

    def get_all_effective_trusts(self) -> Dict[str, float]:
        """返回所有 KOL 的有效信任"""
        return {kol_id: self.get_effective_trust(kol_id) for kol_id in self._states}

    def get_trust_statistics(self) -> dict:
        """全局信任统计"""
        if not self._states:
            return {}
        trusts = [s.effective_trust for s in self._states.values()]
        return {
            "mean_trust": float(np.mean(trusts)),
            "std_trust": float(np.std(trusts)),
            "min_trust": float(np.min(trusts)),
            "max_trust": float(np.max(trusts)),
            "kol_count": len(self._states),
        }

    def summary(self) -> dict:
        """信任引擎状态摘要"""
        return {
            "total_kols": len(self._states),
            "statistics": self.get_trust_statistics(),
            "top5": sorted(
                [(sid, s.effective_trust) for sid, s in self._states.items()],
                key=lambda x: -x[1]
            )[:5],
        }
