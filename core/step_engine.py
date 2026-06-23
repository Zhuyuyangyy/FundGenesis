"""
core/step_engine.py
====================
P1.3: 统一步骤引擎。

每个 step 的执行顺序：
  1. process_scheduled_events   — 处理计划事件（叙事注入等）
  2. propagate_narratives       — 叙事传播
  3. update_trust               — 信任更新
  4. update_beliefs             — 信念更新
  5. update_emotions            — 情绪更新（含叙事→情绪）
  6. agents_decide              — Agent 决策与下单
  7. market_match_or_aggregate  — 市场撮合/聚合
  8. update_price               — 价格更新
  9. compute_reflexivity_metrics — 反身性指标计算
 10. detect_risk                — 风险检测
 11. apply_regulation           — 监管干预（用上一步 risk_score）
 12. record_snapshot            — 记录快照

任何模块不得绕过 StepEngine 直接改价格。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import numpy as np

from core.world_state import WorldState
from core.event_bus import EventBus, Event, EventType


@dataclass
class EngineConfig:
    """引擎配置"""
    steps: int = 200
    seed: Optional[int] = None
    # 市场参数
    initial_price: float = 100.0
    impact_coefficient: float = 0.5
    noise_std: float = 0.008
    total_agents: int = 100
    # 情绪参数
    initial_fear: float = 0.3
    initial_greed: float = 0.3
    initial_confidence: float = 0.5
    initial_uncertainty: float = 0.3
    emotion_inertia: float = 0.90
    # KOL 网络参数
    n_macro: int = 3
    n_influencer: int = 8
    n_micro: int = 15
    n_retail: int = 100
    # Agent 配置
    value_investor_ratio: float = 0.10
    trend_follower_ratio: float = 0.30
    emotional_retail_ratio: float = 0.60
    # 监管参数
    regulation_mode: str = "none"  # "none" / "light" / "strong"
    force_strong_at_step: int = 30


class StepEngine:
    """
    P1.3: 统一步骤引擎。

    管理每个 step 的执行顺序，确保因果链不断裂。
    所有模块通过 StepEngine 运行，不允许绕过。
    """

    def __init__(
        self,
        config: EngineConfig,
        market,
        emotion,
        kol_network,
        narrative_engine,
        propagation_model,
        trust_engine,
        belief_updater,
        reflexivity_monitor,
        risk_agent,
        agents: List,
        regulator=None,
        event_bus: Optional[EventBus] = None,
    ):
        self.config = config
        self.market = market
        self.emotion = emotion
        self.kol_network = kol_network
        self.narrative_engine = narrative_engine
        self.propagation_model = propagation_model
        self.trust_engine = trust_engine
        self.belief_updater = belief_updater
        self.reflexivity_monitor = reflexivity_monitor
        self.risk_agent = risk_agent
        self.agents = agents
        self.regulator = regulator
        self.event_bus = event_bus or EventBus()

        # 状态跟踪
        self.snapshots: List[WorldState] = []
        self.prev_risk_score: float = 0.0
        self.prev_bubble_risk: float = 0.0
        self._strong_active: bool = False
        self._step_count: int = 0

        # 计划事件回调（由外部设置）
        self._scheduled_event_handler: Optional[Callable[[int], None]] = None

        if config.seed is not None:
            np.random.seed(config.seed)

    def set_scheduled_event_handler(self, handler: Callable[[int], None]):
        """设置计划事件处理器（如叙事注入）"""
        self._scheduled_event_handler = handler

    def run(self, verbose: bool = False) -> List[WorldState]:
        """运行完整仿真"""
        for step in range(self.config.steps):
            self.step(step, verbose=verbose)
        return self.snapshots

    def step(self, step: int, verbose: bool = False):
        """
        执行单个 step，严格按 12 步顺序。
        """
        self._step_count = step
        self.event_bus.emit(Event(
            event_type=EventType.STEP_STARTED, step=step, source="step_engine",
            payload={"step": step}
        ))

        # ── 1. process_scheduled_events ──
        if self._scheduled_event_handler is not None:
            self._scheduled_event_handler(step)

        # ── 2. propagate_narratives ──
        self.propagation_model.step()
        self.narrative_engine.tick()

        # ── 3. update_trust ──
        # trust_engine 在 belief_updater 中间接更新

        # ── 4. update_beliefs ──
        self.belief_updater.update_all(
            agents=self.agents, market=self.market, emotion=self.emotion,
            kol_network=self.kol_network, narrative_engine=self.narrative_engine,
        )

        # ── 5. update_emotions ──
        price_change = self.market.price_change_pct if self.market.price_history else 0.0
        self.narrative_engine.propagate_to_emotion(self.emotion, price_change_pct=price_change)

        # ── 6. agents_decide ──
        self.market.begin_step()
        for agent in self.agents:
            action = agent.decide(self.market.get_snapshot(), self.emotion)
            volume = agent.get_trade_volume()
            self.market.submit_order(agent.agent_id, action.value, volume)

        # ── 7+8. market_match + update_price ──
        self.market.update_price(self.emotion)
        self.market.end_step()
        self.emotion.decay_toward_neutral(inertia=self.config.emotion_inertia)

        # ── 11. apply_regulation（在 risk 评估之前，用上一步 risk_score）──
        interventions = []
        if self.regulator is not None and self.config.regulation_mode != "none":
            interventions = self._apply_regulation(step)

        # ── 9. compute_reflexivity_metrics ──
        metrics = self.reflexivity_monitor.observe(
            step=step, market=self.market, emotion=self.emotion,
            kol_network=self.kol_network, narrative_engine=self.narrative_engine,
            agents=self.agents,
        )

        # ── 10. detect_risk ──
        risk_report = self.risk_agent.evaluate(
            step=step, kol_network=self.kol_network, trust_engine=self.trust_engine,
            reflexivity_monitor=self.reflexivity_monitor, market=self.market,
            narrative_engine=self.narrative_engine,
            propagation_model=self.propagation_model, agents=self.agents,
        )

        # FOMO → EmotionField 闭环
        if risk_report.fomo_score > 0.3:
            self.emotion.apply_fomo_signal(
                intensity=risk_report.fomo_score,
                source="manipulation_risk_agent",
                decay=0.85,
            )
            self.event_bus.emit(Event(
                event_type=EventType.EMOTION_UPDATED, step=step, source="fomo_linkage",
                payload={"fomo_score": risk_report.fomo_score, "greed_after": self.emotion.greed}
            ))

        # 保存本步 risk_score 供下一步干预使用
        self.prev_risk_score = risk_report.manipulation_risk_score
        self.prev_bubble_risk = metrics.bubble_risk_score

        # ── 12. record_snapshot ──
        snapshot = WorldState.snapshot(
            step=step,
            market=self.market,
            emotion=self.emotion,
            narrative_engine=self.narrative_engine,
            agents=self.agents,
            kol_network=self.kol_network,
            risk_report=risk_report,
            metrics=metrics,
            interventions=interventions if interventions else None,
        )
        self.snapshots.append(snapshot)

        self.event_bus.emit(Event(
            event_type=EventType.STEP_COMPLETED, step=step, source="step_engine",
            payload={
                "price": self.market.price,
                "risk_score": risk_report.manipulation_risk_score,
                "bubble_risk": metrics.bubble_risk_score,
            }
        ))

        if verbose and step % 15 == 0:
            print(f"  Step {step:>4d} | Price {self.market.price:>7.2f} | "
                  f"Risk {risk_report.manipulation_risk_score:.3f} | "
                  f"Bubble {metrics.bubble_risk_score:.3f}")

    def _apply_regulation(self, step: int) -> List:
        """应用监管干预"""
        from risk.regulator_agent import (
            InterventionIntensity, InterventionAction,
            InterventionEffect,
        )

        interventions = []

        if self.config.regulation_mode == "strong":
            # Strong 模式：强制触发并保持
            if step == self.config.force_strong_at_step:
                self._strong_active = True
                print(f"[Step {step}] [REGULATOR] ★ STRONG INTERVENTION triggered")

            if self._strong_active:
                self.regulator.current_intensity = InterventionIntensity.STRONG
                risk_for_action = max(self.prev_risk_score, 0.5)
                for action_flag in [
                    InterventionAction.NARRATIVE_THROTTLE,
                    InterventionAction.KOL_DOWNWEIGHT,
                    InterventionAction.RISK_WARNING,
                    InterventionAction.TRADING_COOLDOWN,
                ]:
                    self.regulator._apply_action(action_flag, risk_for_action, InterventionEffect(step=step, actions=[]))
                self.regulator._apply_to_narrative_engine(self.narrative_engine, risk_for_action)
                self.regulator._apply_to_kol_network(self.kol_network, risk_for_action)
                self.regulator._apply_to_agents(self.agents, risk_for_action)
                effect = InterventionEffect(step=step, actions=[
                    a.value for a in [
                        InterventionAction.NARRATIVE_THROTTLE,
                        InterventionAction.KOL_DOWNWEIGHT,
                        InterventionAction.RISK_WARNING,
                        InterventionAction.TRADING_COOLDOWN,
                    ]
                ])
                self.regulator.history.append(effect)
                interventions.append(effect)

                self.event_bus.emit(Event(
                    event_type=EventType.INTERVENTION_APPLIED, step=step, source="regulator",
                    payload={"mode": "strong", "actions": effect.actions}
                ))
            else:
                effect = self.regulator.step(
                    risk_score=self.prev_risk_score,
                    market_state={"price": self.market.price, "bubble_risk": self.prev_bubble_risk},
                    narrative_engine=self.narrative_engine,
                    kol_network=self.kol_network,
                    agents=self.agents,
                )
                if effect.actions:
                    interventions.append(effect)

        elif self.config.regulation_mode == "light":
            effect = self.regulator.step(
                risk_score=self.prev_risk_score,
                market_state={"price": self.market.price, "bubble_risk": self.prev_bubble_risk},
                narrative_engine=self.narrative_engine,
                kol_network=self.kol_network,
                agents=self.agents,
            )
            if effect.actions:
                interventions.append(effect)

        return interventions

    def get_results(self) -> Dict[str, Any]:
        """获取仿真结果摘要"""
        if not self.snapshots:
            return {}

        risk_scores = [s.risk.manipulation_risk_score for s in self.snapshots]
        bubble_scores = [s.risk.bubble_risk_score for s in self.snapshots]
        prices = [s.market.price for s in self.snapshots]
        high_risk_steps = sum(1 for r in risk_scores if r >= 0.25)

        return {
            "steps": len(self.snapshots),
            "peak_manipulation_risk": max(risk_scores) if risk_scores else 0.0,
            "peak_bubble_risk": max(bubble_scores) if bubble_scores else 0.0,
            "high_risk_steps": high_risk_steps,
            "final_price": prices[-1] if prices else 0.0,
            "price_peak": max(prices) if prices else 0.0,
            "final_drawdown_pct": (prices[-1] / max(prices) - 1) * 100 if prices else 0.0,
            "price_change_pct": (prices[-1] / prices[0] - 1) * 100 if prices else 0.0,
        }
