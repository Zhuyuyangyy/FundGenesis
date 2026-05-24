from __future__ import annotations

"""
trust/trust_bootstrapper.py
===========================
V0.3：信任初始化引导器（Trust Bootstrapper）。

负责：
1. 基于 KOL 层级（tier）分配初始信任锚定
2. 混入历史信誉分（如果有历史记录）
3. 提供"低信任场景"和"高信任场景"两种预设

层级 → 初始信任映射（可配置）：
  MACRO      → 0.80  (机构/顶级媒体，自带权威)
  INFLUENCER → 0.60  (中型KOL，有一定粉丝基础)
  MICRO      → 0.35  (小V/群主，信任度参差不齐)
  RETAIL     → 0.25  (普通投资者，最低信任锚)

Demo 场景预设：
  LOW_TRUST_REGIME：  所有信任分 × 0.3（叙事难以扩散）
  HIGH_TRUST_REGIME： 所有信任分 × 1.0（叙事快速引爆）
  FALSIFICATION_REGIME：叙事证伪时触发信任崩塌
"""

from dataclasses import dataclass
from typing import Optional, List
import numpy as np

from social.kol_network import KOLNetwork, KOLTier
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_engine import TrustConfig as EngineConfig


@dataclass
class BootstrapConfig:
    """Bootstrap 配置"""
    # 各层级的基础信任分
    trust_macro: float = 0.80
    trust_influencer: float = 0.60
    trust_micro: float = 0.35
    trust_retail: float = 0.25

    # 初始信誉分（历史准确率，无历史时设为中性值）
    initial_credibility: float = 0.50

    # 初始价格验证系数
    initial_price_validation: float = 0.50

    # 社会证明初始值（追随者数归一化，启动时由 TrustEngine.update_follower_counts 处理）
    initial_social_proof: float = 0.30

    # 随机噪声（模拟信任不确定性）
    noise_std: float = 0.05


class TrustBootstrapper:
    """
    信任初始化引导器。

    使用方法：
        bootstrapper = TrustBootstrapper(config)
        bootstrapper.bootstrap_network(network, trust_engine)

        # 低信任 Demo 场景
        bootstrapper.apply_low_trust_regime(trust_engine, network)
    """

    def __init__(self, config: Optional[BootstrapConfig] = None):
        self.config = config or BootstrapConfig()

    def bootstrap_network(self,
                          network: KOLNetwork,
                          trust_engine: TrustEngine) -> None:
        """
        将网络中所有 KOL 节点初始化信任状态。
        调用时机：仿真开始前。
        """
        tier_map = {
            KOLTier.MACRO: self.config.trust_macro,
            KOLTier.INFLUENCER: self.config.trust_influencer,
            KOLTier.MICRO: self.config.trust_micro,
            KOLTier.RETAIL: self.config.trust_retail,
        }

        for kol in network.get_kols():
            base_trust = tier_map.get(kol.tier, self.config.trust_retail)
            # 加入随机噪声（模拟信任不确定性）
            noisy_trust = base_trust + np.random.normal(0, self.config.noise_std)
            noisy_trust = float(np.clip(noisy_trust, 0.0, 1.0))

            trust_engine.init_kol(kol.node_id, initial_trust=noisy_trust)
            trust_engine.set_credibility_score(
                kol.node_id, self.config.initial_credibility
            )
            trust_engine.set_price_validation(
                kol.node_id, self.config.initial_price_validation
            )

    def apply_low_trust_regime(self,
                               trust_engine: TrustEngine,
                               network: KOLNetwork,
                               multiplier: float = 0.3) -> None:
        """
        低信任场景：所有 KOL 信任分压低 × multiplier。
        用于 Demo 4：低信任 KOL 传播失败。
        """
        for kol in network.get_kols():
            state = trust_engine.get_state(kol.node_id)
            if state:
                new_trust = float(np.clip(state.trust_level * multiplier, 0.0, 1.0))
                trust_engine.set_trust_level(kol.node_id, new_trust)

    def apply_high_trust_regime(self,
                                trust_engine: TrustEngine,
                                network: KOLNetwork,
                                target_trust: float = 0.95) -> None:
        """
        高信任场景：顶级 KOL 信任分拉满到 target_trust。
        用于 Demo 5：高信任 KOL 引爆共识。
        """
        for kol in network.get_kols():
            if kol.tier == KOLTier.MACRO:
                trust_engine.set_trust_level(kol.node_id, target_trust)
                trust_engine.set_credibility_score(kol.node_id, 0.90)
            elif kol.tier == KOLTier.INFLUENCER:
                trust_engine.set_trust_level(kol.node_id, target_trust * 0.8)
                trust_engine.set_credibility_score(kol.node_id, 0.80)

    def apply_falsification_regime(self,
                                   trust_engine: TrustEngine,
                                   network: KOLNetwork,
                                   kol_ids: Optional[List[str]] = None,
                                   penalty: float = 0.6) -> None:
        """
        叙事证伪场景：指定 KOL（默认全部）的信任分崩塌。
        用于 Demo 6：反向证据摧毁信任。
        """
        targets = []
        if kol_ids:
            targets = [network.get_node(kid) for kid in kol_ids if network.get_node(kid)]
        else:
            targets = network.get_kols()

        for kol in targets:
            state = trust_engine.get_state(kol.node_id)
            if state:
                # 信任崩塌：大幅下降
                new_trust = float(np.clip(state.trust_level * (1.0 - penalty), 0.0, 1.0))
                trust_engine.set_trust_level(kol.node_id, new_trust)
                # 信誉分同步下降
                new_cred = float(np.clip(state.credibility_score * (1.0 - penalty * 0.8), 0.0, 1.0))
                trust_engine.set_credibility_score(kol.node_id, new_cred)
                # 价格验证系数归零（预测失败）
                trust_engine.set_price_validation(kol.node_id, 0.0)

    def get_initial_trust_for_tier(self, tier: KOLTier) -> float:
        """查询某层级的初始信任分"""
        return {
            KOLTier.MACRO: self.config.trust_macro,
            KOLTier.INFLUENCER: self.config.trust_influencer,
            KOLTier.MICRO: self.config.trust_micro,
            KOLTier.RETAIL: self.config.trust_retail,
        }.get(tier, self.config.trust_retail)
