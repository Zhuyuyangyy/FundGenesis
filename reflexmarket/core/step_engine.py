"""
reflexmarket/core/step_engine.py
===================================
Standardized 16-phase simulation step lifecycle.
"""

from __future__ import annotations
from typing import Any
from reflexmarket.core.world_state import WorldState
from reflexmarket.core.event_bus import EventBus


class StepEngine:
    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus or EventBus()

    def run_step(self, world: WorldState, scheduled_events: list[dict] | None = None) -> WorldState:
        step = world.step
        self.event_bus.emit(step, "StepStarted", "StepEngine")

        # Phase 1: Reset market step
        world.market.begin_step()
        self.event_bus.emit(step, "MarketStepBegan", "StepEngine")

        # Phase 2: Apply regulation
        self._apply_regulation(world)

        # Phase 3: Process scheduled events
        self._process_scheduled_events(world, scheduled_events or [])

        # Phase 4-5: Propagate narratives
        if world.propagation is not None:
            world.propagation.step()
        if world.narrative_engine is not None:
            world.narrative_engine.tick()

        # Phase 6: Update beliefs
        if world.belief_updater is not None:
            world.belief_updater.update_all(
                agents=world.agents, market=world.market, emotion=world.emotion,
                kol_network=world.kol_network, narrative_engine=world.narrative_engine,
            )

        # Phase 7: Narrative → Emotion
        if world.narrative_engine is not None and world.market is not None:
            price_change = world.market.price_change_pct if world.market.price_history else 0.0
            world.narrative_engine.propagate_to_emotion(world.emotion, price_change_pct=price_change)

        # Phase 8: Agents decide
        self._agents_decide(world)

        # Phase 9: Market price update
        world.market.update_price(world.emotion)

        # Phase 10: Reflexivity monitor
        if world.reflexivity_monitor is not None:
            world.metrics = world.reflexivity_monitor.observe(
                step=step, market=world.market, emotion=world.emotion,
                kol_network=world.kol_network, narrative_engine=world.narrative_engine,
                agents=world.agents,
            )
            world.metrics_history.append(world.metrics)
            world.current_bubble_risk = world.metrics.bubble_risk_score
            world.current_panic_risk = world.metrics.panic_risk_score

        # Phase 11: Risk evaluation
        self._evaluate_risk(world)

        # Phase 12: FOMO → EmotionField
        self._apply_fomo_to_emotion(world)

        # Phase 13-14: State decay
        if world.emotion is not None:
            world.emotion.decay_toward_neutral(inertia=0.90)
        if world.kol_network is not None:
            world.kol_network.decay_beliefs_all()

        # Phase 15: Record metrics
        self.event_bus.emit(step, "StepCompleted", "StepEngine",
            price=world.market.price if world.market else 0.0,
            risk_score=world.current_risk_score, bubble_risk=world.current_bubble_risk)

        # Phase 16: Advance step
        world.prev_risk_score = world.current_risk_score
        world.step += 1
        return world

    def _apply_regulation(self, world: WorldState) -> None:
        if world.regulator is None or world.regulation_mode == "baseline":
            return
        if world.current_risk_score < 0.15:
            return
        manipulation_flags = {
            "coordinated_detected": False,
            "fomo_detected": world.current_risk_score > 0.3,
            "self_validation_detected": False,
        }
        market_state = {
            "price": world.market.price if world.market else 100.0,
            "bubble_risk": world.current_bubble_risk,
            "retail_fomo": world.current_risk_score * 0.5,
            "price_volatility": 0.01,
        }
        effect = world.regulator.step(
            risk_score=world.current_risk_score, market_state=market_state,
            manipulation_flags=manipulation_flags, narrative_engine=world.narrative_engine,
            kol_network=world.kol_network, agents=world.agents,
        )
        if effect.actions:
            self.event_bus.emit(world.step, "RegulationApplied", "Regulator",
                actions=[a.value if hasattr(a, 'value') else str(a) for a in effect.actions],
                reports=[{"action": r.action, "verified": r.verified} for r in effect.effect_reports])
        if world.regulator.state.warning_active:
            fear_inject = world.regulator.state.investor_fear_factor * 0.15
            world.emotion.fear = min(world.emotion.fear + fear_inject, 1.0)
            world.emotion.uncertainty = min(world.emotion.uncertainty + fear_inject * 0.5, 1.0)
            world.emotion.greed = max(world.emotion.greed - fear_inject * 0.3, 0.0)

    def _process_scheduled_events(self, world: WorldState, events: list[dict]) -> None:
        for event in events:
            event_type = event.get("type", "")
            if event_type == "narrative_inject":
                self._inject_narrative(world, event)
            elif event_type == "kol_spread":
                self._record_kol_spread(world, event)
            elif event_type == "price_feedback":
                self._record_price_feedback(world, event)
            elif event_type == "fomo_signal":
                self._record_fomo_signal(world, event)

    def _inject_narrative(self, world: WorldState, event: dict) -> None:
        from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
        narrative = NarrativeEvent(
            name=event.get("narrative", "unnamed"),
            category=NarrativeCategory[event.get("category", "EARNINGS")],
            polarity=Polarity[event.get("polarity", "POSITIVE")],
            target_sector=event.get("sector", "tech"),
            intensity=event.get("intensity", 0.80),
            credibility=event.get("credibility", 0.75),
            novelty=event.get("novelty", 0.85),
            duration=event.get("duration", 80),
            source=event.get("source", "scenario"),
        )
        world.narrative_engine.inject(narrative)
        if world.propagation is not None:
            world.propagation.inject_narrative(narrative)
        world.active_narrative = narrative
        self.event_bus.emit(world.step, "NarrativeInjected", "Scenario",
            narrative=narrative.name, intensity=narrative.intensity)

    def _record_kol_spread(self, world: WorldState, event: dict) -> None:
        if world.risk_agent is None or world.active_narrative is None:
            return
        for kol_id in event.get("kol_ids", []):
            world.risk_agent.record_kol_spread(world.active_narrative._id, kol_id)
        self.event_bus.emit(world.step, "KOLSpread", "Scenario", kol_ids=event.get("kol_ids", []))

    def _record_price_feedback(self, world: WorldState, event: dict) -> None:
        if world.risk_agent is None or world.active_narrative is None:
            return
        world.risk_agent.record_price_feedback(
            narrative_id=world.active_narrative._id,
            price_change=event.get("price_change", 0.03),
            confirmation_strength=event.get("confirmation_strength", 0.72),
            step=world.step)
        self.event_bus.emit(world.step, "PriceFeedback", "Scenario")

    def _record_fomo_signal(self, world: WorldState, event: dict) -> None:
        if world.risk_agent is None:
            return
        world.risk_agent.record_fomo_signal(
            retail_buy_ratio=event.get("retail_buy_ratio", 0.78),
            greed_level=event.get("greed_level", 0.82),
            belief_concentration=event.get("belief_concentration", 0.70),
            step=world.step)
        self.event_bus.emit(world.step, "FOMOSignal", "Scenario")

    def _agents_decide(self, world: WorldState) -> None:
        for agent in world.agents:
            action = agent.decide(world.market.get_snapshot(), world.emotion)
            volume = agent.get_trade_volume()
            world.market.submit_order(agent.agent_id, action.value, volume)

    def _evaluate_risk(self, world: WorldState) -> None:
        if world.risk_agent is None:
            return
        risk_report = world.risk_agent.evaluate(
            step=world.step, kol_network=world.kol_network,
            trust_engine=world.trust_engine, reflexivity_monitor=world.reflexivity_monitor,
            market=world.market, narrative_engine=world.narrative_engine,
            propagation_model=world.propagation, agents=world.agents)
        world.current_risk_score = risk_report.manipulation_risk_score
        world.current_manipulation_risk = risk_report.manipulation_risk_score

    def _apply_fomo_to_emotion(self, world: WorldState) -> None:
        if world.risk_agent is None or world.emotion is None:
            return
        fomo_impulse = world.risk_agent.get_fomo_emotion_impulse()
        if fomo_impulse > 0.1:
            world.emotion.apply_fomo_signal(fomo_impulse)
            self.event_bus.emit(world.step, "FOMOAppliedToEmotion", "StepEngine", impulse=fomo_impulse)
