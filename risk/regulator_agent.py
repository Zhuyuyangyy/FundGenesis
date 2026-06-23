"""
risk/regulator_agent.py
========================
RegulatorAgent V0.5 — 监管干预Agent

接入 ManipulationRiskAgent 的风险输出，执行干预动作：

4个干预动作:
- narrative_throttle:  叙事限流（降低NarrativeEngine生成速率/强度）
- kol_downweight:      KOL降权（降低高信任KOL的影响力）
- risk_warning:         风险提示（向市场发出风险信号）
- trading_cooldown:    交易冷却（减少散户短期交易频率）

干预强度分级:
- NONE (risk < 0.30):  无干预
- LIGHT (0.30-0.50):  narrative_throttle + risk_warning
- MODERATE (0.50-0.70): + kol_downweight
- STRONG (>= 0.70):   + trading_cooldown

Demo验收指标:
- peak_risk 是否下降
- high_risk_steps 是否减少
- bubble_risk_score 是否下降
- retail_fomo_surge 是否减弱
- price_volatility 是否降低
- final_drawdown 是否更可控
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import numpy as np


class InterventionAction(Enum):
    NARRATIVE_THROTTLE = "narrative_throttle"
    KOL_DOWNWEIGHT     = "kol_downweight"
    RISK_WARNING        = "risk_warning"
    TRADING_COOLDOWN   = "trading_cooldown"
    NO_ACTION          = "no_action"


class InterventionIntensity(Enum):
    NONE     = 0
    LIGHT    = 1
    MODERATE = 2
    STRONG   = 3


@dataclass
class InterventionEffect:
    """单步干预效果"""
    step: int
    actions: List[str]
    risk_reduction: float = 0.0
    narrative_suppression: float = 0.0
    fomo_reduction: float = 0.0
    price_volatility_change: float = 0.0
    bubble_risk_delta: float = 0.0


@dataclass
class InterventionEffectReport:
    """
    P0.5: 干预效果验证报告。

    每个干预动作必须能回答：
    改了谁？改了什么字段？改前是多少？改后是多少？是否影响后续step？
    """
    action: str
    targets: int
    field_changed: str
    before_mean: float
    after_mean: float
    verified: bool
    step: int


@dataclass
class RegulatorState:
    """监管状态机"""
    narrative_cap: float = 1.0          # 叙事生成上限倍率
    kol_penalty: float = 1.0            # KOL影响力惩罚
    trading_slowdown: float = 0.0        # 交易频率降低
    warning_active: bool = False
    warning_strength: float = 0.0
    warning_steps_remaining: int = 0
    cooldown_steps_remaining: int = 0
    investor_fear_factor: float = 0.0    # 投资者恐惧放大因子


class InterventionPolicy:
    """干预策略：根据风险评分选择干预强度"""
    LIGHT_THRESHOLD    = 0.30
    MODERATE_THRESHOLD = 0.50
    STRONG_THRESHOLD   = 0.70

    @classmethod
    def select_intensity(cls, risk_score: float) -> InterventionIntensity:
        if risk_score < cls.LIGHT_THRESHOLD:
            return InterventionIntensity.NONE
        elif risk_score < cls.MODERATE_THRESHOLD:
            return InterventionIntensity.LIGHT
        elif risk_score < cls.STRONG_THRESHOLD:
            return InterventionIntensity.MODERATE
        else:
            return InterventionIntensity.STRONG

    @classmethod
    def get_actions(cls, intensity: InterventionIntensity) -> List[InterventionAction]:
        if intensity == InterventionIntensity.NONE:
            return [InterventionAction.NO_ACTION]
        elif intensity == InterventionIntensity.LIGHT:
            return [InterventionAction.NARRATIVE_THROTTLE, InterventionAction.RISK_WARNING]
        elif intensity == InterventionIntensity.MODERATE:
            return [InterventionAction.NARRATIVE_THROTTLE,
                    InterventionAction.KOL_DOWNWEIGHT,
                    InterventionAction.RISK_WARNING]
        else:
            return [InterventionAction.NARRATIVE_THROTTLE,
                    InterventionAction.KOL_DOWNWEIGHT,
                    InterventionAction.RISK_WARNING,
                    InterventionAction.TRADING_COOLDOWN]


class CoolingMechanism:
    """交易冷却机制"""
    BASE_STEPS  = 6
    MAX_STEPS   = 18

    @classmethod
    def compute_duration(cls, risk_score: float, intensity: InterventionIntensity) -> int:
        dur = int(cls.BASE_STEPS * risk_score)
        if intensity == InterventionIntensity.STRONG:
            dur = int(dur * 1.6)
        return min(dur, cls.MAX_STEPS)


class InvestorProtection:
    """投资者保护机制"""
    WARNING_DECAY_STEPS = 10

    @classmethod
    def issue_warning(cls, state: RegulatorState, risk_score: float):
        state.warning_active = True
        state.warning_strength = min(risk_score * 1.2, 1.0)
        state.warning_steps_remaining = cls.WARNING_DECAY_STEPS
        state.investor_fear_factor = min(risk_score * 1.4, 1.0)

    @classmethod
    def decay_warning(cls, state: RegulatorState):
        if state.warning_steps_remaining > 0:
            state.warning_steps_remaining -= 1
            decay_ratio = state.warning_steps_remaining / cls.WARNING_DECAY_STEPS
            state.warning_strength = state.warning_strength * decay_ratio
            if state.warning_steps_remaining == 0:
                state.warning_active = False
                state.investor_fear_factor = 0.0


class RegulatorAgent:
    """
    监管Agent

    使用方法:
        regulator = RegulatorAgent()

        for step in range(1000):
            risk_report = risk_agent.evaluate(...)   # ManipulationRiskAgent
            intervention = regulator.step(
                risk_score=risk_report.manipulation_risk_score,
                market_state={...},
            )
            # regulator自动修改 market, narrative_engine, kol_network 状态
    """

    def __init__(self):
        self.state = RegulatorState()
        self.history: List[InterventionEffect] = []
        self.effect_reports: List[InterventionEffectReport] = []  # P0.5
        self.current_intensity = InterventionIntensity.NONE
        self._step_count = 0

    def reset(self):
        self.state = RegulatorState()
        self.history.clear()
        self.effect_reports.clear()  # P0.5
        self.current_intensity = InterventionIntensity.NONE
        self._step_count = 0

    def step(self,
             risk_score: float,
             market_state: Dict,
             manipulation_flags: Optional[Dict] = None,
             narrative_engine=None,
             kol_network=None,
             agents: List = None) -> InterventionEffect:
        """
        执行监管干预

        Args:
            risk_score: ManipulationRiskAgent输出的风险评分
            market_state: 市场状态字典 {price, bubble_risk, retail_fomo, ...}
            manipulation_flags: 来自ManipulationRiskAgent的标志位
            narrative_engine: NarrativeEngine引用（用于限流）
            kol_network: KOLNetwork引用（用于降权）
            agents: Agent列表（用于交易冷却）

        Returns:
            InterventionEffect: 干预效果记录
        """
        self._step_count += 1

        # 警告自然衰减
        InvestorProtection.decay_warning(self.state)

        # 冷却衰减
        if self.state.cooldown_steps_remaining > 0:
            self.state.cooldown_steps_remaining -= 1
            if self.state.cooldown_steps_remaining == 0:
                self.state.trading_slowdown = 0.0

        # 干预强度降级（风险降低时）
        new_intensity = InterventionPolicy.select_intensity(risk_score)
        if new_intensity.value < self.current_intensity.value:
            # 逐步退出干预
            self._apply_deescalation(new_intensity)
            self.current_intensity = new_intensity
        elif new_intensity.value > self.current_intensity.value:
            self.current_intensity = new_intensity

        # 执行干预动作
        actions = InterventionPolicy.get_actions(self.current_intensity)
        effect = InterventionEffect(step=self._step_count, actions=[])

        for action in actions:
            if action == InterventionAction.NO_ACTION:
                continue
            self._apply_action(action, risk_score, effect)

        # 应用到具体组件
        if narrative_engine is not None:
            self._apply_to_narrative_engine(narrative_engine, risk_score)

        if kol_network is not None:
            self._apply_to_kol_network(kol_network, risk_score)

        if agents is not None:
            self._apply_to_agents(agents, risk_score)

        effect.bubble_risk_delta = -effect.risk_reduction * 0.3
        self.history.append(effect)

        return effect

    def _apply_action(self, action: InterventionAction, risk_score: float, effect: InterventionEffect):
        """应用单个干预动作"""
        effect.actions.append(action.value)

        if action == InterventionAction.NARRATIVE_THROTTLE:
            # 叙事限流：降低叙事生成强度和传播速度
            self.state.narrative_cap = max(1.0 - risk_score * 0.55, 0.25)
            effect.narrative_suppression = risk_score * 0.55

        elif action == InterventionAction.KOL_DOWNWEIGHT:
            # KOL降权：降低KOL影响力，削弱协同传播
            self.state.kol_penalty = max(1.0 - risk_score * 0.65, 0.15)
            effect.risk_reduction += risk_score * 0.35

        elif action == InterventionAction.RISK_WARNING:
            # 风险提示：发出市场警告，触发投资者谨慎
            InvestorProtection.issue_warning(self.state, risk_score)
            effect.risk_reduction += risk_score * 0.25

        elif action == InterventionAction.TRADING_COOLDOWN:
            # 交易冷却：减少短期交易频率
            dur = CoolingMechanism.compute_duration(risk_score, self.current_intensity)
            self.state.cooldown_steps_remaining = dur
            self.state.trading_slowdown = min(risk_score * 0.75, 0.75)
            effect.risk_reduction += risk_score * 0.40
            effect.fomo_reduction = risk_score * 0.30

    def _apply_to_narrative_engine(self, engine, risk_score: float):
        """
        P0.5: 将叙事限流应用到NarrativeEngine，并生成效果验证报告。

        narrative_throttle: 直接写入 engine.narrative_strength_multiplier
        """
        before_multiplier = engine.narrative_strength_multiplier
        engine.narrative_strength_multiplier = self.state.narrative_cap
        after_multiplier = engine.narrative_strength_multiplier

        # P0.5: 生成效果验证报告
        report = InterventionEffectReport(
            action="narrative_throttle",
            targets=1,
            field_changed="narrative_strength_multiplier",
            before_mean=round(before_multiplier, 4),
            after_mean=round(after_multiplier, 4),
            verified=(after_multiplier < before_multiplier),
            step=self._step_count,
        )
        self.effect_reports.append(report)

    def _apply_to_kol_network(self, network, risk_score: float):
        """
        P0.5: 将KOL降权应用到KOLNetwork，并生成效果验证报告。

        修复：使用正确的字段名 influence_score（而非 influence_weight），
        并记录干预前后的值变化。
        """
        kols = network.get_kols()
        if not kols:
            return

        # 记录干预前
        before_influence = float(np.mean([k.influence_score for k in kols]))
        before_trust = float(np.mean([k.trust_level for k in kols]))

        for kol in kols:
            # P0.5 修复：使用正确的字段名 influence_score
            kol.influence_score *= self.state.kol_penalty
            kol.trust_level *= self.state.kol_penalty

        # 记录干预后
        after_influence = float(np.mean([k.influence_score for k in kols]))
        after_trust = float(np.mean([k.trust_level for k in kols]))

        # P0.5: 生成效果验证报告
        report = InterventionEffectReport(
            action="kol_downweight",
            targets=len(kols),
            field_changed="influence_score, trust_level",
            before_mean=round(before_influence, 4),
            after_mean=round(after_influence, 4),
            verified=(after_influence < before_influence),
            step=self._step_count,
        )
        self.effect_reports.append(report)

    def _apply_to_agents(self, agents: List, risk_score: float):
        """
        P0.5: 将交易冷却应用到Agent列表，并生成效果验证报告。
        """
        slowdown = self.state.trading_slowdown
        if slowdown <= 0 and not self.state.warning_active:
            return

        # 记录干预前
        before_trade_freq = []
        before_fomo_sens = []
        for agent in agents:
            if hasattr(agent, 'trade_frequency'):
                before_trade_freq.append(agent.trade_frequency)
            if hasattr(agent, 'fomo_sensitivity'):
                before_fomo_sens.append(agent.fomo_sensitivity)

        for agent in agents:
            if hasattr(agent, 'trade_frequency'):
                agent.trade_frequency *= (1.0 - slowdown)
            if hasattr(agent, 'fomo_sensitivity') and self.state.warning_active:
                # 风险警告时，散户FOMO敏感度降低
                agent.fomo_sensitivity *= (1.0 - self.state.investor_fear_factor * 0.5)

        # P0.5: 生成效果验证报告
        if before_trade_freq:
            after_trade_freq = [a.trade_frequency for a in agents if hasattr(a, 'trade_frequency')]
            report = InterventionEffectReport(
                action="trading_cooldown",
                targets=len(before_trade_freq),
                field_changed="trade_frequency",
                before_mean=round(float(np.mean(before_trade_freq)), 4),
                after_mean=round(float(np.mean(after_trade_freq)), 4) if after_trade_freq else 0.0,
                verified=(len(after_trade_freq) > 0 and float(np.mean(after_trade_freq)) < float(np.mean(before_trade_freq))),
                step=self._step_count,
            )
            self.effect_reports.append(report)

        if before_fomo_sens and self.state.warning_active:
            after_fomo_sens = [a.fomo_sensitivity for a in agents if hasattr(a, 'fomo_sensitivity')]
            report = InterventionEffectReport(
                action="risk_warning",
                targets=len(before_fomo_sens),
                field_changed="fomo_sensitivity",
                before_mean=round(float(np.mean(before_fomo_sens)), 4),
                after_mean=round(float(np.mean(after_fomo_sens)), 4) if after_fomo_sens else 0.0,
                verified=(len(after_fomo_sens) > 0 and float(np.mean(after_fomo_sens)) < float(np.mean(before_fomo_sens))),
                step=self._step_count,
            )
            self.effect_reports.append(report)

    def _apply_deescalation(self, new_intensity: InterventionIntensity):
        """干预降级：逐步撤销干预动作"""
        if new_intensity.value <= InterventionIntensity.LIGHT.value:
            # MODERATE->LIGHT: 只保留 throttle + warning
            self.state.kol_penalty = 1.0
        if new_intensity == InterventionIntensity.NONE:
            # 完全撤销
            self.state.narrative_cap = 1.0
            self.state.kol_penalty = 1.0
            self.state.trading_slowdown = 0.0
            self.state.warning_active = False
            self.state.investor_fear_factor = 0.0

    def get_summary(self) -> Dict:
        """干预历史摘要"""
        if not self.history:
            return {"total_interventions": 0}
        return {
            "total_interventions": len(self.history),
            "avg_risk_reduction": np.mean([e.risk_reduction for e in self.history]),
            "avg_narrative_suppression": np.mean([e.narrative_suppression for e in self.history]),
            "avg_fomo_reduction": np.mean([e.fomo_reduction for e in self.history]),
            "current_state": {
                "narrative_cap": round(self.state.narrative_cap, 3),
                "kol_penalty": round(self.state.kol_penalty, 3),
                "trading_slowdown": round(self.state.trading_slowdown, 3),
                "warning_active": self.state.warning_active,
                "cooldown_remaining": self.state.cooldown_steps_remaining,
            }
        }

    @property
    def active_interventions(self) -> List[str]:
        active = []
        if self.state.narrative_cap < 0.95:
            active.append("narrative_throttle")
        if self.state.kol_penalty < 0.95:
            active.append("kol_downweight")
        if self.state.trading_slowdown > 0.05:
            active.append("trading_cooldown")
        if self.state.warning_active:
            active.append("risk_warning")
        return active