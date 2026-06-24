"""
core/scenario_runner.py
========================
P1.4: 场景运行器。

使用 ScenarioConfig + StepEngine 运行仿真实验，
替代写死 Python demo 的方式。
"""

import os, sys, json, numpy as np
from typing import Dict, Any, Optional

from core.scenario_config import ScenarioConfig, NarrativeInjection
from core.step_engine import StepEngine, EngineConfig
from core.world_state import WorldState
from core.event_bus import EventBus
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor
from trust.trust_engine import TrustEngine, TrustConfig
from risk.manipulation_risk_agent import ManipulationRiskAgent
from risk.regulator_agent import RegulatorAgent
from agents.value_investor import ValueInvestorAgent
from agents.trend_follower import TrendFollowerAgent
from agents.emotional_retail import EmotionalRetailAgent


# NarrativeCategory 和 Polarity 的字符串映射
CATEGORY_MAP = {
    "policy": NarrativeCategory.POLICY,
    "sector": NarrativeCategory.SECTOR,
    "macro": NarrativeCategory.MACRO,
    "fintech": NarrativeCategory.FINTECH,
    "regulatory": NarrativeCategory.REGULATORY,
    "earnings": NarrativeCategory.EARNINGS,
    "manipulation": NarrativeCategory.MANIPULATION,
    "sentiment": NarrativeCategory.SENTIMENT,
}

POLARITY_MAP = {
    "positive": Polarity.POSITIVE,
    "negative": Polarity.NEGATIVE,
    "neutral": Polarity.NEUTRAL,
}


class ScenarioRunner:
    """
    P1.4: 场景运行器。

    用法：
        config = ScenarioConfig.from_yaml("scenarios/A01.yaml")
        runner = ScenarioRunner(config)
        results = runner.run()
    """

    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.event_bus = EventBus()
        self.engine: Optional[StepEngine] = None
        self.snapshots: list = []

    def _build_components(self):
        """根据配置构建所有组件"""
        cfg = self.config

        # 设置随机种子
        if cfg.seed is not None:
            np.random.seed(cfg.seed)

        # 市场
        market = MarketEnvironment()
        market.reset(
            initial_price=cfg.market.initial_price,
            impact_coefficient=cfg.market.impact_coefficient,
            noise_std=cfg.market.noise_std,
            total_agents=cfg.market.total_agents,
        )

        # 情绪
        emotion = EmotionField(
            fear=cfg.emotion.initial_fear,
            greed=cfg.emotion.initial_greed,
            confidence=cfg.emotion.initial_confidence,
            uncertainty=cfg.emotion.initial_uncertainty,
        )

        # KOL 网络
        kol_network = KOLNetwork().build_default_network(
            n_macro=cfg.kol.n_macro,
            n_influencer=cfg.kol.n_influencer,
            n_micro=cfg.kol.n_micro,
            n_retail=cfg.kol.n_retail,
        )

        # 叙事引擎
        narrative_engine = NarrativeEngine()
        propagation_model = PropagationModel(kol_network)

        # 信任引擎
        trust_engine = TrustEngine(TrustConfig())

        # 信念更新器
        belief_updater = BeliefUpdaterV2()

        # 监控
        reflexivity_monitor = ReflexivityMonitor()

        # 风险 Agent
        risk_agent = ManipulationRiskAgent(
            action_thresholds={
                "monitor": cfg.regulation.monitor_threshold,
                "human_review": cfg.regulation.human_review_threshold,
                "block": cfg.regulation.block_threshold,
            }
        )

        # 监管 Agent
        regulator = RegulatorAgent() if cfg.regulation.mode != "none" else None

        # Agents
        n_total = cfg.market.total_agents
        n_vi = int(n_total * cfg.agents.value_investor_ratio)
        n_tf = int(n_total * cfg.agents.trend_follower_ratio)
        n_er = n_total - n_vi - n_tf

        agents = []
        for i in range(n_vi):
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        for i in range(n_tf):
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        for i in range(n_er):
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

        return {
            "market": market,
            "emotion": emotion,
            "kol_network": kol_network,
            "narrative_engine": narrative_engine,
            "propagation_model": propagation_model,
            "trust_engine": trust_engine,
            "belief_updater": belief_updater,
            "reflexivity_monitor": reflexivity_monitor,
            "risk_agent": risk_agent,
            "regulator": regulator,
            "agents": agents,
        }

    def _build_scheduled_event_handler(self, components):
        """构建叙事注入处理器"""
        cfg = self.config
        narrative_engine = components["narrative_engine"]
        propagation_model = components["propagation_model"]
        injected = set()

        def handler(step: int):
            for ninj in cfg.narratives:
                if ninj.step == step and ninj.step not in injected:
                    injected.add(ninj.step)
                    category = CATEGORY_MAP.get(ninj.category, NarrativeCategory.FINTECH)
                    polarity = POLARITY_MAP.get(ninj.polarity, Polarity.POSITIVE)
                    narrative = NarrativeEvent(
                        name=ninj.name or f"narrative_step_{step}",
                        category=category,
                        polarity=polarity,
                        target_sector=ninj.target_sector,
                        intensity=ninj.intensity,
                        credibility=ninj.credibility,
                    )
                    narrative_engine.inject(narrative)
                    propagation_model.inject_narrative(narrative)

        return handler

    def run(self, verbose: bool = False) -> Dict[str, Any]:
        """运行仿真场景"""
        components = self._build_components()

        engine_config = EngineConfig(
            steps=self.config.steps,
            seed=self.config.seed,
            initial_price=self.config.market.initial_price,
            impact_coefficient=self.config.market.impact_coefficient,
            noise_std=self.config.market.noise_std,
            total_agents=self.config.market.total_agents,
            initial_fear=self.config.emotion.initial_fear,
            initial_greed=self.config.emotion.initial_greed,
            initial_confidence=self.config.emotion.initial_confidence,
            initial_uncertainty=self.config.emotion.initial_uncertainty,
            emotion_inertia=self.config.emotion.inertia,
            n_macro=self.config.kol.n_macro,
            n_influencer=self.config.kol.n_influencer,
            n_micro=self.config.kol.n_micro,
            n_retail=self.config.kol.n_retail,
            value_investor_ratio=self.config.agents.value_investor_ratio,
            trend_follower_ratio=self.config.agents.trend_follower_ratio,
            emotional_retail_ratio=self.config.agents.emotional_retail_ratio,
            regulation_mode=self.config.regulation.mode,
            force_strong_at_step=self.config.regulation.force_strong_at_step,
        )

        self.engine = StepEngine(
            config=engine_config,
            event_bus=self.event_bus,
            **components,
        )

        # 设置叙事注入处理器
        self.engine.set_scheduled_event_handler(
            self._build_scheduled_event_handler(components)
        )

        # 运行
        if verbose:
            print(f"\n{'='*60}")
            print(f"Scenario: {self.config.id} — {self.config.name}")
            print(f"{'='*60}")
            print(f"  Steps: {self.config.steps}, Seed: {self.config.seed}")
            print(f"  Regulation: {self.config.regulation.mode}")
            print(f"  Narratives: {len(self.config.narratives)} injections")
            print(f"\n{'Step':>6} | {'Price':>7} | {'Risk':>6} | {'Bubble':>6}")
            print("-" * 45)

        self.engine.run(verbose=verbose)

        # 获取结果
        results = self.engine.get_results()
        self.snapshots = self.engine.snapshots

        # 验收
        validation = self.config.validate_results(results)

        if verbose:
            print(f"\n{'='*60}")
            print(f"RESULTS — {self.config.id}")
            print(f"{'='*60}")
            print(f"  peak_manipulation_risk: {results.get('peak_manipulation_risk', 0):.4f}")
            print(f"  peak_bubble_risk:      {results.get('peak_bubble_risk', 0):.4f}")
            print(f"  high_risk_steps:       {results.get('high_risk_steps', 0)}")
            print(f"  final_drawdown:        {results.get('final_drawdown_pct', 0):.2f}%")
            if validation:
                print(f"\n  Validation:")
                for check, passed in validation.items():
                    status = "PASS" if passed else "FAIL"
                    print(f"    {check}: {status}")

        return {
            "scenario_id": self.config.id,
            "results": results,
            "validation": validation,
            "snapshots": len(self.snapshots),
            "events": self.event_bus.event_count,
        }
