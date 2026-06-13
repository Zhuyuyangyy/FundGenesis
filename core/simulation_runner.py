"""
core/simulation_runner.py
==========================
Unified Market Simulation Runner (统一仿真运行器)

Orchestrates all components into a single simulation loop:
  CreatorController -> MarketEnvironment -> EmotionField -> Agents
  -> NarrativeEngine -> KOLNetwork -> PropagationModel -> TrustEngine
  -> ReflexivityMonitor -> ManipulationRiskAgent -> RegulatorAgent
  -> ReflexivityGameModel -> RiskPropagationEngine

This is the main entry point for running complete financial simulations.

Usage:
    from core.simulation_runner import SimulationRunner, SimulationConfig

    config = SimulationConfig(
        n_steps=200,
        n_retail=50,
        n_trend=20,
        n_value=10,
        narrative_events=[...],
    )
    runner = SimulationRunner(config)
    results = runner.run()
    runner.save_results("outputs/sim_result.json")
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json
import time
import logging
import numpy as np

logger = logging.getLogger('FundGenesis.simulation')


@dataclass
class SimulationConfig:
    """Configuration for a simulation run"""
    # Simulation parameters
    n_steps: int = 200
    initial_price: float = 100.0
    fundamental_value: float = 100.0
    impact_coefficient: float = 0.15
    noise_std: float = 0.01

    # Agent population
    n_retail: int = 50
    n_trend: int = 20
    n_value: int = 10

    # KOL network
    n_macro_kol: int = 2
    n_influencer: int = 5
    n_micro_kol: int = 10
    n_network_retail: int = 100

    # Narrative events (list of dicts with timing)
    narrative_events: List[Dict] = field(default_factory=list)

    # External shocks
    shocks: List[Dict] = field(default_factory=list)

    # Random seed
    seed: Optional[int] = None

    # Component toggles
    enable_reflexivity_game: bool = True
    enable_risk_propagation: bool = True
    enable_regulator: bool = True
    enable_trust_engine: bool = True

    # Logging
    log_every: int = 50
    quiet: bool = False


@dataclass
class SimulationStepResult:
    """Result from a single simulation step"""
    step: int
    price: float
    price_change_pct: float
    volatility: float
    order_imbalance: float

    # Emotion
    fear: float
    greed: float
    fear_greed_index: float

    # Agents
    buy_count: int
    sell_count: int
    hold_count: int
    mean_belief: float
    belief_std: float

    # Narrative
    active_narratives: int
    narrative_strength: float

    # Reflexivity monitor
    reflexivity_index: float
    bubble_risk: float
    panic_risk: float
    regime: str

    # Game theory (optional)
    game_regime: Optional[str] = None
    nash_distance: Optional[float] = None
    polarization: Optional[float] = None

    # Risk propagation (optional)
    system_risk: Optional[float] = None
    cascade_count: Optional[int] = None

    # Manipulation risk
    manipulation_risk: float = 0.0

    def as_dict(self) -> dict:
        d = {
            "step": self.step,
            "price": round(self.price, 4),
            "price_change_pct": round(self.price_change_pct, 6),
            "volatility": round(self.volatility, 6),
            "order_imbalance": round(self.order_imbalance, 4),
            "fear": round(self.fear, 4),
            "greed": round(self.greed, 4),
            "fear_greed_index": round(self.fear_greed_index, 4),
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "hold_count": self.hold_count,
            "mean_belief": round(self.mean_belief, 4),
            "belief_std": round(self.belief_std, 4),
            "active_narratives": self.active_narratives,
            "narrative_strength": round(self.narrative_strength, 4),
            "reflexivity_index": round(self.reflexivity_index, 4),
            "bubble_risk": round(self.bubble_risk, 4),
            "panic_risk": round(self.panic_risk, 4),
            "regime": self.regime,
            "manipulation_risk": round(self.manipulation_risk, 4),
        }
        if self.game_regime:
            d["game_regime"] = self.game_regime
            d["nash_distance"] = round(self.nash_distance, 4) if self.nash_distance is not None else None
            d["polarization"] = round(self.polarization, 4) if self.polarization is not None else None
        if self.system_risk is not None:
            d["system_risk"] = round(self.system_risk, 4)
            d["cascade_count"] = self.cascade_count
        return d


@dataclass
class SimulationResult:
    """Complete simulation result"""
    config: SimulationConfig
    steps: List[SimulationStepResult]
    duration_seconds: float
    final_price: float
    max_bubble_risk: float
    max_panic_risk: float
    regime_distribution: Dict[str, int]
    peak_price: float
    trough_price: float
    total_return: float

    def as_dict(self) -> dict:
        return {
            "config": {
                "n_steps": self.config.n_steps,
                "initial_price": self.config.initial_price,
                "n_retail": self.config.n_retail,
                "n_trend": self.config.n_trend,
                "n_value": self.config.n_value,
                "seed": self.config.seed,
            },
            "summary": {
                "duration_seconds": round(self.duration_seconds, 2),
                "final_price": round(self.final_price, 2),
                "max_bubble_risk": round(self.max_bubble_risk, 4),
                "max_panic_risk": round(self.max_panic_risk, 4),
                "peak_price": round(self.peak_price, 2),
                "trough_price": round(self.trough_price, 2),
                "total_return": round(self.total_return, 4),
                "regime_distribution": self.regime_distribution,
            },
            "steps": [s.as_dict() for s in self.steps],
        }


class SimulationRunner:
    """
    Unified Simulation Runner.

    Orchestrates all FundGenesis components into a coherent simulation.

    Usage:
        config = SimulationConfig(n_steps=200, n_retail=50)
        runner = SimulationRunner(config)
        result = runner.run()
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        if config.seed is not None:
            np.random.seed(config.seed)

        self._result: Optional[SimulationResult] = None
        self._step_results: List[SimulationStepResult] = []

    def run(self) -> SimulationResult:
        """Run the complete simulation."""
        start_time = time.time()
        cfg = self.config

        if not cfg.quiet:
            logger.info(f"Starting simulation: {cfg.n_steps} steps, "
                       f"{cfg.n_retail + cfg.n_trend + cfg.n_value} agents")

        # ── Initialize components ────────────────────────────────

        # 1. Creator Controller
        from core.creator_controller import CreatorController, MarketConfig, ShockConfig
        creator = CreatorController(
            market_config=MarketConfig(
                initial_price=cfg.initial_price,
                impact_coefficient=cfg.impact_coefficient,
                noise_std=cfg.noise_std,
                total_agents=cfg.n_retail + cfg.n_trend + cfg.n_value,
            )
        )
        for shock in cfg.shocks:
            creator.shocks.append(ShockConfig(**shock))

        # 2. Market Environment
        market = creator.setup_market()
        market.fundamental_value = cfg.fundamental_value

        # 3. Emotion Field
        emotion = creator.setup_emotion()

        # 4. Agents
        from agents.emotional_retail import EmotionalRetail
        from agents.trend_follower import TrendFollower
        from agents.value_investor import ValueInvestor

        agents = []
        for i in range(cfg.n_retail):
            agents.append(EmotionalRetail(f"retail_{i:03d}"))
        for i in range(cfg.n_trend):
            agents.append(TrendFollower(f"trend_{i:03d}"))
        for i in range(cfg.n_value):
            agents.append(ValueInvestor(f"value_{i:03d}", fair_value=cfg.fundamental_value))

        # 5. KOL Network
        from social.kol_network import KOLNetwork
        kol_network = KOLNetwork().build_default_network(
            n_macro=cfg.n_macro_kol,
            n_influencer=cfg.n_influencer,
            n_micro=cfg.n_micro_kol,
            n_retail=cfg.n_network_retail,
        )

        # 6. Propagation Model
        from social.propagation_model import PropagationModel
        propagation = PropagationModel(kol_network)

        # 7. Narrative Engine
        from narrative.narrative_engine import NarrativeEngine
        from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
        narrative_engine = NarrativeEngine()

        # 8. Belief Updater
        from core.belief_updater_v2 import BeliefUpdaterV2
        belief_updater = BeliefUpdaterV2()

        # 9. Reflexivity Monitor
        from monitor.reflexivity_monitor import ReflexivityMonitor
        reflexivity_monitor = ReflexivityMonitor()

        # 10. Trust Engine
        trust_engine = None
        if cfg.enable_trust_engine:
            from trust.trust_engine import TrustEngine
            trust_engine = TrustEngine()
            for kol in kol_network.get_kols():
                trust_engine.init_kol(kol.node_id, kol.trust_level)

        # 11. Risk Agent
        from risk.manipulation_risk_agent import ManipulationRiskAgent
        risk_agent = ManipulationRiskAgent()

        # 12. Regulator
        regulator = None
        if cfg.enable_regulator:
            from risk.regulator_agent import RegulatorAgent
            regulator = RegulatorAgent()

        # 13. Reflexivity Game Model
        game_model = None
        if cfg.enable_reflexivity_game:
            from core.reflexivity_game import ReflexivityGameModel
            game_model = ReflexivityGameModel()

        # 14. Risk Propagation Engine
        risk_prop = None
        if cfg.enable_risk_propagation:
            from core.risk_propagation import RiskPropagationEngine, RiskSource
            risk_prop = RiskPropagationEngine()
            risk_prop.build_from_kol_network(kol_network, agents)

        # ── Simulation Loop ──────────────────────────────────────

        self._step_results = []
        narrative_schedule = self._build_narrative_schedule(cfg)

        for step in range(cfg.n_steps):
            step_result = self._run_step(
                step=step,
                market=market,
                emotion=emotion,
                agents=agents,
                kol_network=kol_network,
                propagation_model=propagation,
                narrative_engine=narrative_engine,
                belief_updater=belief_updater,
                reflexivity_monitor=reflexivity_monitor,
                trust_engine=trust_engine,
                risk_agent=risk_agent,
                regulator=regulator,
                game_model=game_model,
                risk_prop=risk_prop,
                creator=creator,
                narrative_schedule=narrative_schedule,
            )
            self._step_results.append(step_result)

            if not cfg.quiet and step % cfg.log_every == 0:
                logger.info(
                    f"Step {step}/{cfg.n_steps}: "
                    f"price={step_result.price:.2f}, "
                    f"bubble_risk={step_result.bubble_risk:.3f}, "
                    f"regime={step_result.regime}"
                )

        # ── Compute Results ──────────────────────────────────────

        duration = time.time() - start_time
        prices = [s.price for s in self._step_results]

        regime_dist = {}
        for s in self._step_results:
            r = s.regime
            regime_dist[r] = regime_dist.get(r, 0) + 1

        self._result = SimulationResult(
            config=cfg,
            steps=self._step_results,
            duration_seconds=duration,
            final_price=prices[-1] if prices else cfg.initial_price,
            max_bubble_risk=max(s.bubble_risk for s in self._step_results) if self._step_results else 0.0,
            max_panic_risk=max(s.panic_risk for s in self._step_results) if self._step_results else 0.0,
            regime_distribution=regime_dist,
            peak_price=max(prices) if prices else cfg.initial_price,
            trough_price=min(prices) if prices else cfg.initial_price,
            total_return=(prices[-1] - cfg.initial_price) / cfg.initial_price if prices else 0.0,
        )

        if not cfg.quiet:
            logger.info(f"Simulation complete in {duration:.2f}s")
            logger.info(f"Final price: {self._result.final_price:.2f}, "
                       f"Return: {self._result.total_return:.2%}")

        return self._result

    def _run_step(self, step, market, emotion, agents, kol_network,
                  propagation_model, narrative_engine, belief_updater,
                  reflexivity_monitor, trust_engine, risk_agent,
                  regulator, game_model, risk_prop, creator,
                  narrative_schedule) -> SimulationStepResult:
        """Execute a single simulation step."""

        # ── 1. Inject narratives ──
        if step in narrative_schedule:
            for event_data in narrative_schedule[step]:
                from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
                event = NarrativeEvent(
                    name=event_data.get("name", f"Event_{step}"),
                    category=NarrativeCategory(event_data.get("category", "sentiment")),
                    polarity=Polarity(event_data.get("polarity", "positive")),
                    intensity=event_data.get("intensity", 0.5),
                    credibility=event_data.get("credibility", 0.6),
                    novelty=event_data.get("novelty", 0.5),
                    duration=event_data.get("duration", 20),
                )
                narrative_engine.inject(event)
                propagation_model.inject_narrative(event)

                # Inject into risk propagation
                if risk_prop and event_data.get("polarity") == "negative":
                    macro_kols = kol_network.get_kols()[:2]
                    for k in macro_kols:
                        risk_prop.inject_risk(
                            k.node_id,
                            event.intensity * 0.5,
                            __import__('core.risk_propagation', fromlist=['RiskSource']).RiskSource.NARRATIVE_SHOCK,
                            step=step,
                        )

        # ── 2. External shocks ──
        shock = creator.check_and_inject_shock(step, market, emotion)

        # ── 3. Propagate narratives ──
        propagation_model.step()

        # ── 4. Update trust ──
        if trust_engine is not None:
            trust_engine.update_follower_counts(kol_network)

        # ── 5. Update beliefs ──
        social_pressure = 0.0
        stats = kol_network.belief_statistics()
        social_pressure = stats.get("mean_belief", 0.0)

        belief_updater.update_all(
            agents=agents,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=narrative_engine,
            social_pressure_override=social_pressure,
        )

        # ── 6. Agent decisions ──
        market.reset_volumes()
        buy_count = 0
        sell_count = 0
        hold_count = 0

        snapshot = market.get_snapshot()
        for agent in agents:
            action = agent.decide(snapshot, emotion)
            volume = agent.get_trade_volume()

            if action.value == "BUY":
                market.submit_order(agent.agent_id, "BUY", volume)
                buy_count += 1
            elif action.value == "SELL":
                market.submit_order(agent.agent_id, "SELL", volume)
                sell_count += 1
            else:
                hold_count += 1

        # ── 7. Update price ──
        market.update_price(emotion)

        # ── 8. Update emotion ──
        emotion.apply_price_change(market.price_change_pct)
        narrative_engine.propagate_to_emotion(emotion, market.price_change_pct)
        emotion.decay_toward_neutral()

        # ── 9. Narrative decay ──
        narrative_engine.tick()

        # ── 10. Reflexivity Monitor ──
        ref_metrics = reflexivity_monitor.observe(
            step=step, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine,
            agents=agents,
        )

        # ── 11. Manipulation Risk ──
        risk_report = risk_agent.evaluate(
            step=step, kol_network=kol_network,
            trust_engine=trust_engine,
            reflexivity_monitor=reflexivity_monitor,
            market=market, narrative_engine=narrative_engine,
            propagation_model=propagation_model, agents=agents,
        )

        # ── 12. Regulator ──
        if regulator is not None:
            regulator.step(
                risk_score=risk_report.manipulation_risk_score,
                market_state={
                    "price": market.price,
                    "bubble_risk": ref_metrics.bubble_risk_score,
                },
                narrative_engine=narrative_engine,
                kol_network=kol_network,
                agents=agents,
            )

        # ── 13. Game Theory Analysis ──
        game_regime = None
        nash_distance = None
        polarization = None
        if game_model is not None:
            game_eq = game_model.analyze(
                agents=agents,
                price_change_pct=market.price_change_pct,
                narrative_signal=narrative_engine.narrative_strength(),
                volatility=market.volatility,
            )
            game_regime = game_eq.regime.value
            nash_distance = game_eq.nash_distance
            polarization = game_eq.polarization_index

        # ── 14. Risk Propagation ──
        system_risk = None
        cascade_count = None
        if risk_prop is not None:
            prop_report = risk_prop.propagate(
                step=step, emotion=emotion,
                price_change_pct=market.price_change_pct,
                volatility=market.volatility,
                narrative_risk=narrative_engine.narrative_strength() * 0.3,
            )
            system_risk = prop_report.system_risk
            cascade_count = len(prop_report.cascade_events)

        # ── Build step result ──
        beliefs = [a.belief for a in agents]

        return SimulationStepResult(
            step=step,
            price=market.price,
            price_change_pct=market.price_change_pct,
            volatility=market.volatility,
            order_imbalance=market.order_imbalance,
            fear=emotion.fear,
            greed=emotion.greed,
            fear_greed_index=emotion.fear_greed_index,
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
            mean_belief=float(np.mean(beliefs)) if beliefs else 0.0,
            belief_std=float(np.std(beliefs)) if beliefs else 0.0,
            active_narratives=len(narrative_engine.registry.active),
            narrative_strength=narrative_engine.narrative_strength(),
            reflexivity_index=ref_metrics.reflexivity_index,
            bubble_risk=ref_metrics.bubble_risk_score,
            panic_risk=ref_metrics.panic_risk_score,
            regime=ref_metrics.regime.value,
            game_regime=game_regime,
            nash_distance=nash_distance,
            polarization=polarization,
            system_risk=system_risk,
            cascade_count=cascade_count,
            manipulation_risk=risk_report.manipulation_risk_score,
        )

    def _build_narrative_schedule(self, config: SimulationConfig) -> Dict[int, List[Dict]]:
        """Build a step -> narrative_events mapping."""
        schedule = {}
        for event in config.narrative_events:
            step = event.get("timing", 0)
            if step not in schedule:
                schedule[step] = []
            schedule[step].append(event)
        return schedule

    @property
    def result(self) -> Optional[SimulationResult]:
        return self._result

    def save_results(self, path: str):
        """Save simulation results to JSON file."""
        if self._result is None:
            logger.warning("No results to save. Run simulation first.")
            return
        import os
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._result.as_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {path}")
