from __future__ import annotations

"""
trust/trust_decay_model.py
===========================
V0.3：信任衰减模型（Trust Decay Model）。

核心问题：
  - KOL 发了叙事之后，如果一直没有价格验证，信任会不会衰减？
  - 答案是：会，但衰减速度和"无验证时长"正相关。

衰减机制：
1. Time Decay（时间衰减）：长期不说话，信任自然下滑
2. No-Validation Decay（无验证衰减）：发了观点但价格没配合，怀疑累积

信任恢复机制：
3. Validation Boost（验证提振）：价格验证了自己的叙事，信任恢复

衰减公式：
  T(t+1) = T(t) - time_decay - no_validation_decay + validation_boost

关键参数：
  - decay_per_step: 每步时间衰减量
  - no_validation_threshold: 多少步没有验证开始算惩罚
  - no_validation_decay_rate: 无验证每次的额外衰减
  - validation_boost_rate: 验证成功时的恢复量
"""

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np

from trust.trust_engine import TrustEngine, TrustConfig


@dataclass
class DecayConfig:
    """衰减模型配置"""
    # 时间衰减：每步信任自然下滑量
    decay_per_step: float = 0.005

    # 无验证衰减：超过这个步数没有价格验证，开始额外衰减
    no_validation_threshold: int = 5

    # 无验证每次额外衰减量
    no_validation_decay_rate: float = 0.01

    # 验证成功时信任恢复量
    validation_boost_rate: float = 0.05

    # 最低信任衰减下限（不会衰减到 0）
    min_trust: float = 0.05


class TrustDecayModel:
    """
    信任衰减模型。

    使用方法：
        decay_model = TrustDecayModel(config)
        decay_model.attach_engine(trust_engine)

        for step in range(100):
            # 先更新验证状态（NarrativeVerificationChecker 在外部驱动）
            decay_model.record_verification_status(kol_id, has_validation)
            # 再推进衰减
            decay_model.tick(network)
    """

    def __init__(self, config: Optional[DecayConfig] = None):
        self.config = config or DecayConfig()
        self._engine: Optional[TrustEngine] = None

        # 内部状态
        self._steps_since_last_verification: Dict[str, int] = {}  # kol_id → 距上次验证的步数
        self._steps_without_any_narrative: Dict[str, int] = {}     # kol_id → 沉默步数
        self._last_narrative_step: Dict[str, int] = {}             # kol_id → 上次发叙事步数

    def attach_engine(self, engine: TrustEngine) -> None:
        """绑定信任引擎"""
        self._engine = engine

    def _ensure_kol_state(self, kol_id: str) -> None:
        """确保 KOL 状态已初始化"""
        if kol_id not in self._steps_since_last_verification:
            self._steps_since_last_verification[kol_id] = 0
        if kol_id not in self._steps_without_any_narrative:
            self._steps_without_any_narrative[kol_id] = 0

    # ── 外部驱动接口（供 Simulation 或 Experiment 调用）────────

    def record_narrative_injection(self, kol_id: str, step: int) -> None:
        """记录某 KOL 在某步注入了叙事"""
        self._ensure_kol_state(kol_id)
        self._last_narrative_step[kol_id] = step
        self._steps_without_any_narrative[kol_id] = 0  # 发言了，重置沉默计数

    def record_verification(self, kol_id: str, step: int) -> None:
        """记录某 KOL 的叙事在某步被价格验证（预测正确）"""
        self._ensure_kol_state(kol_id)
        self._steps_since_last_verification[kol_id] = 0
        if self._engine:
            state = self._engine.get_state(kol_id)
            if state:
                # 验证成功 → 信任恢复
                new_trust = min(1.0, state.trust_level + self.config.validation_boost_rate)
                self._engine.set_trust_level(kol_id, new_trust)

    def record_failed_verification(self, kol_id: str, step: int) -> None:
        """记录某 KOL 的叙事在某步被证伪（预测错误）"""
        self._ensure_kol_state(kol_id)
        self._steps_since_last_verification[kol_id] = 0  # 重置（已有证伪惩罚在 updater 里）
        if self._engine:
            state = self._engine.get_state(kol_id)
            if state:
                # 证伪 → 信任额外损失（比无验证更重）
                penalty = self.config.no_validation_decay_rate * 2.0
                new_trust = max(
                    self.config.min_trust,
                    state.trust_level - penalty
                )
                self._engine.set_trust_level(kol_id, new_trust)

    def tick(self, network: KOLNetwork, current_step: int) -> None:
        """
        每步推进信任衰减。
        在 Simulation 主循环中调用（在 belief update 之后，价格 update 之前）。
        """
        if self._engine is None:
            return

        for kol in network.get_kols():
            self._ensure_kol_state(kol.node_id)
            kid = kol.node_id

            # 1. 时间衰减（每次 tick 都扣一点）
            state = self._engine.get_state(kid)
            if state:
                new_trust = max(
                    self.config.min_trust,
                    state.trust_level - self.config.decay_per_step
                )
                self._engine.set_trust_level(kid, new_trust)

            # 2. 沉默衰减（该 KOL 超过阈值步数没发言）
            if kid in self._last_narrative_step:
                silent_steps = current_step - self._last_narrative_step[kid]
                if silent_steps > 0:
                    extra_decay = (
                        (silent_steps - self.config.no_validation_threshold)
                        * self.config.no_validation_decay_rate
                        if silent_steps > self.config.no_validation_threshold
                        else 0.0
                    )
                    if extra_decay > 0 and state:
                        new_trust = max(
                            self.config.min_trust,
                            state.trust_level - extra_decay
                        )
                        self._engine.set_trust_level(kid, new_trust)

            # 3. 无验证衰减（发了叙事但没有价格确认）
            if kid in self._steps_since_last_verification:
                if kid in self._last_narrative_step:
                    # 发了叙事之后才开始算无验证
                    narrative_step = self._last_narrative_step[kid]
                    no_val_steps = current_step - narrative_step
                    if no_val_steps > self.config.no_validation_threshold:
                        extra = (
                            (no_val_steps - self.config.no_validation_threshold)
                            * self.config.no_validation_decay_rate
                        )
                        if extra > 0 and state:
                            new_trust = max(
                                self.config.min_trust,
                                state.trust_level - extra
                            )
                            self._engine.set_trust_level(kid, new_trust)

    def get_decay_report(self, network: KOLNetwork) -> dict:
        """生成衰减报告"""
        if self._engine is None:
            return {}
        report = {}
        for kol in network.get_kols():
            kid = kol.node_id
            state = self._engine.get_state(kid)
            if state:
                last_narr = self._last_narrative_step.get(kid, 0)
                report[kid] = {
                    "name": kol.name,
                    "tier": kol.tier.value,
                    "current_trust": round(state.trust_level, 4),
                    "effective_trust": round(state.effective_trust, 4),
                    "steps_since_last_narrative": last_narr,
                    "has_active_narrative": (
                        kid in self._last_narrative_step
                        and (state.trust_level > self.config.min_trust)
                    ),
                }
        return report
