"""
reflexmarket/core/simulation_runner.py
=========================================
From-config initialization and execution.
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
import numpy as np
from reflexmarket.core.world_state import WorldState
from reflexmarket.core.event_bus import EventBus
from reflexmarket.core.step_engine import StepEngine
from reflexmarket.core.scenario_config import ScenarioConfig


class SimulationRunner:
    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.event_bus = EventBus()
        self.engine = StepEngine(self.event_bus)
        self.world: WorldState | None = None

    def initialize(self) -> WorldState:
        project_root = str(Path(__file__).resolve().parent.parent.parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        np.random.seed(self.config.seed)

        from core.creator_controller import CreatorController, MarketConfig
        from core.emotion_field import EmotionField
        from core.belief_updater_v2 import BeliefUpdaterV2
        from social.kol_network import KOLNetwork
        from social.propagation_model import PropagationModel
        from narrative.narrative_engine import NarrativeEngine
        from monitor.reflexivity_monitor import ReflexivityMonitor
        from trust.trust_engine import TrustEngine, TrustConfig
        from trust.trust_bootstrapper import TrustBootstrapper
        from risk.manipulation_risk_agent import ManipulationRiskAgent
        from agents.emotional_retail import EmotionalRetailAgent
        from agents.trend_follower import TrendFollowerAgent
        from agents.value_investor import ValueInvestorAgent

        market_cfg = self.config.market
        controller = CreatorController(
            market_config=MarketConfig(
                initial_price=market_cfg.get("initial_price", 100.0),
                impact_coefficient=market_cfg.get("impact_coefficient", 0.20),
                noise_std=market_cfg.get("noise_std", 0.008),
                total_agents=market_cfg.get("total_agents", 100),
            ),
            emotion_config={
                "initial_fear": self.config.emotion.get("initial_fear", 0.15),
                "initial_greed": self.config.emotion.get("initial_greed", 0.60),
                "fear_inertia": self.config.emotion.get("fear_inertia", 0.92),
                "greed_inertia": self.config.emotion.get("greed_inertia", 0.92),
            }
        )
        market = controller.setup_market()
        emotion = controller.setup_emotion()

        kol_cfg = self.config.agents.get("kol", {})
        kol_network = KOLNetwork().build_default_network(
            n_macro=kol_cfg.get("n_macro", 2), n_influencer=kol_cfg.get("n_influencer", 5),
            n_micro=kol_cfg.get("n_micro", 10), n_retail=kol_cfg.get("n_retail", 100))

        narrative_engine = NarrativeEngine()
        propagation = PropagationModel(kol_network)
        belief_updater = BeliefUpdaterV2()
        trust_engine = TrustEngine(TrustConfig())
        TrustBootstrapper().bootstrap_network(kol_network, trust_engine)
        reflexivity_monitor = ReflexivityMonitor()
        risk_agent = ManipulationRiskAgent(action_thresholds={"monitor": 0.15, "human_review": 0.25, "block": 0.60})

        regulation_mode = self.config.regulation.get("mode", "baseline")
        regulator = None
        if regulation_mode != "baseline":
            from risk.regulator_agent import RegulatorAgent
            regulator = RegulatorAgent()

        agents = []
        for i in range(self.config.agents.get("n_value_investor", 10)):
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        for i in range(self.config.agents.get("n_trend_follower", 30)):
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        for i in range(self.config.agents.get("n_retail_agent", 60)):
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

        self.world = WorldState(
            step=0, seed=self.config.seed, market=market, emotion=emotion,
            narrative_engine=narrative_engine, kol_network=kol_network,
            trust_engine=trust_engine, belief_updater=belief_updater,
            propagation=propagation, reflexivity_monitor=reflexivity_monitor,
            risk_agent=risk_agent, regulator=regulator, agents=agents,
            regulation_mode=regulation_mode)
        return self.world

    def run(self) -> dict[str, Any]:
        if self.world is None:
            self.initialize()
        world = self.world
        events_by_step: dict[int, list[dict]] = {}
        for event in self.config.scheduled_events:
            events_by_step.setdefault(event.get("step", 0), []).append(event)
        for step in range(self.config.steps):
            scheduled = events_by_step.get(step, [])
            self.engine.run_step(world, scheduled)
        return self._collect_results(world)

    def _collect_results(self, world: WorldState) -> dict[str, Any]:
        manipulation_high_risk_steps = 0
        bubble_high_risk_steps = 0
        panic_high_risk_steps = 0
        overall_high_risk_steps = 0
        peak_bubble = 0.0
        for m in world.metrics_history:
            risk_score = getattr(m, 'manipulation_risk_score', 0.0)
            bubble_risk = getattr(m, 'bubble_risk_score', 0.0)
            panic_risk = getattr(m, 'panic_risk_score', 0.0)
            if risk_score >= 0.25: manipulation_high_risk_steps += 1
            if bubble_risk >= 0.30: bubble_high_risk_steps += 1
            if panic_risk >= 0.30: panic_high_risk_steps += 1
            if max(bubble_risk, panic_risk) >= 0.30: overall_high_risk_steps += 1
            if bubble_risk > peak_bubble: peak_bubble = bubble_risk

        peak_price = world.market.price
        for p in (world.market.price_history or []):
            if p > peak_price: peak_price = p
        final_price = world.market.price
        drawdown = (final_price - peak_price) / peak_price * 100 if peak_price > 0 else 0.0
        intervention_events = self.event_bus.events_of("RegulationApplied")

        return {
            "scenario_id": self.config.id, "scenario_name": self.config.name,
            "category": self.config.category, "seed": self.config.seed,
            "steps": self.config.steps, "regulation_mode": world.regulation_mode,
            "final_price": round(final_price, 2), "peak_price": round(peak_price, 2),
            "max_drawdown": round(drawdown, 2),
            "peak_bubble_risk": round(peak_bubble, 4),
            "bubble_high_risk_steps": bubble_high_risk_steps,
            "manipulation_high_risk_steps": manipulation_high_risk_steps,
            "panic_high_risk_steps": panic_high_risk_steps,
            "overall_high_risk_steps": overall_high_risk_steps,
            "intervention_count": len(intervention_events),
            "event_count": len(self.event_bus.events),
        }


def run_scenario(config_path: str | Path) -> dict[str, Any]:
    config = ScenarioConfig.from_yaml(config_path)
    runner = SimulationRunner(config)
    return runner.run()
