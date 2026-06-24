"""
tests/regression/test_p1_kernel.py
====================================
P1 仿真内核重构测试。

验证：
  P1.1: WorldState 快照完整性
  P1.2: EventBus 事件记录与查询
  P1.3: StepEngine 执行顺序与因果链
  P1.4: ScenarioConfig YAML 驱动实验
"""

import pytest
import numpy as np
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── P1.1: WorldState ──────────────────────────────────────────

class TestWorldState:
    """P1.1: 验证 WorldState 快照完整性"""

    def test_snapshot_contains_all_modules(self):
        """快照应包含所有模块状态"""
        from core.world_state import WorldState
        from core.market_environment import MarketEnvironment
        from core.emotion_field import EmotionField

        market = MarketEnvironment()
        market.reset()
        emotion = EmotionField()

        snap = WorldState.snapshot(
            step=0, market=market, emotion=emotion,
            narrative_engine=None, agents=[], kol_network=None,
        )

        assert snap.step == 0
        assert snap.market.price == 100.0
        assert snap.emotion.greed == 0.3
        assert isinstance(snap.narratives, list)
        assert isinstance(snap.agents, list)

    def test_snapshot_serializable(self):
        """快照应可序列化为字典"""
        from core.world_state import WorldState
        from core.market_environment import MarketEnvironment
        from core.emotion_field import EmotionField

        market = MarketEnvironment()
        market.reset()
        emotion = EmotionField()

        snap = WorldState.snapshot(
            step=5, market=market, emotion=emotion,
            narrative_engine=None, agents=[], kol_network=None,
        )
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert d["step"] == 5
        assert "market" in d
        assert "emotion" in d


# ── P1.2: EventBus ──────────────────────────────────────────

class TestEventBus:
    """P1.2: 验证 EventBus 事件记录与查询"""

    def test_emit_and_query(self):
        """发射事件后应能查询到"""
        from core.event_bus import EventBus, Event, EventType

        bus = EventBus()
        bus.emit(Event(
            event_type=EventType.PRICE_UPDATED,
            step=10,
            source="market",
            payload={"price": 105.0},
        ))

        events = bus.query(event_type=EventType.PRICE_UPDATED)
        assert len(events) == 1
        assert events[0].payload["price"] == 105.0

    def test_query_by_step(self):
        """应能按步数查询事件"""
        from core.event_bus import EventBus, Event, EventType

        bus = EventBus()
        for step in range(5):
            bus.emit(Event(
                event_type=EventType.STEP_COMPLETED,
                step=step,
                source="engine",
            ))

        step_3_events = bus.query(step=3)
        assert len(step_3_events) == 1
        assert step_3_events[0].step == 3

    def test_subscribe(self):
        """订阅回调应被调用"""
        from core.event_bus import EventBus, Event, EventType

        bus = EventBus()
        received = []
        bus.subscribe(EventType.RISK_DETECTED, lambda e: received.append(e))

        bus.emit(Event(
            event_type=EventType.RISK_DETECTED,
            step=5,
            source="risk_agent",
            payload={"score": 0.8},
        ))

        assert len(received) == 1
        assert received[0].payload["score"] == 0.8

    def test_timeline(self):
        """时间线应返回序列化的事件列表"""
        from core.event_bus import EventBus, Event, EventType

        bus = EventBus()
        bus.emit(Event(event_type=EventType.STEP_STARTED, step=0, source="engine"))
        bus.emit(Event(event_type=EventType.STEP_COMPLETED, step=0, source="engine"))

        timeline = bus.get_timeline(0, 0)
        assert len(timeline) == 2
        assert all(isinstance(t, dict) for t in timeline)


# ── P1.3: StepEngine ──────────────────────────────────────────

class TestStepEngine:
    """P1.3: 验证 StepEngine 执行顺序与因果链"""

    def test_engine_runs_and_produces_snapshots(self):
        """引擎运行后应产生快照"""
        from core.step_engine import StepEngine, EngineConfig
        from core.market_environment import MarketEnvironment
        from core.emotion_field import EmotionField
        from social.kol_network import KOLNetwork
        from social.propagation_model import PropagationModel
        from narrative.narrative_engine import NarrativeEngine
        from monitor.reflexivity_monitor import ReflexivityMonitor
        from trust.trust_engine import TrustEngine, TrustConfig
        from core.belief_updater_v2 import BeliefUpdaterV2
        from risk.manipulation_risk_agent import ManipulationRiskAgent
        from agents.value_investor import ValueInvestorAgent
        from agents.trend_follower import TrendFollowerAgent
        from agents.emotional_retail import EmotionalRetailAgent

        np.random.seed(42)
        market = MarketEnvironment()
        market.reset(total_agents=10)
        emotion = EmotionField()
        kol_network = KOLNetwork().build_default_network(n_macro=1, n_influencer=2, n_micro=3, n_retail=10)
        narrative_engine = NarrativeEngine()
        propagation = PropagationModel(kol_network)
        trust_engine = TrustEngine(TrustConfig())
        belief_updater = BeliefUpdaterV2()
        monitor = ReflexivityMonitor()
        risk_agent = ManipulationRiskAgent()

        agents = [ValueInvestorAgent("V0"), TrendFollowerAgent("T0"), EmotionalRetailAgent("E0")]

        config = EngineConfig(steps=5, seed=42, total_agents=10)
        engine = StepEngine(
            config=config, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine,
            propagation_model=propagation, trust_engine=trust_engine,
            belief_updater=belief_updater, reflexivity_monitor=monitor,
            risk_agent=risk_agent, agents=agents,
        )

        engine.run()

        assert len(engine.snapshots) == 5
        assert engine.snapshots[0].step == 0
        assert engine.snapshots[4].step == 4

    def test_engine_results_summary(self):
        """引擎应返回结果摘要"""
        from core.step_engine import StepEngine, EngineConfig
        from core.market_environment import MarketEnvironment
        from core.emotion_field import EmotionField
        from social.kol_network import KOLNetwork
        from social.propagation_model import PropagationModel
        from narrative.narrative_engine import NarrativeEngine
        from monitor.reflexivity_monitor import ReflexivityMonitor
        from trust.trust_engine import TrustEngine, TrustConfig
        from core.belief_updater_v2 import BeliefUpdaterV2
        from risk.manipulation_risk_agent import ManipulationRiskAgent
        from agents.emotional_retail import EmotionalRetailAgent

        np.random.seed(42)
        market = MarketEnvironment()
        market.reset(total_agents=5)
        emotion = EmotionField()
        kol_network = KOLNetwork().build_default_network(n_macro=1, n_influencer=1, n_micro=1, n_retail=5)
        narrative_engine = NarrativeEngine()
        propagation = PropagationModel(kol_network)
        trust_engine = TrustEngine(TrustConfig())
        belief_updater = BeliefUpdaterV2()
        monitor = ReflexivityMonitor()
        risk_agent = ManipulationRiskAgent()
        agents = [EmotionalRetailAgent(f"E{i}") for i in range(5)]

        config = EngineConfig(steps=10, seed=42, total_agents=5)
        engine = StepEngine(
            config=config, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine,
            propagation_model=propagation, trust_engine=trust_engine,
            belief_updater=belief_updater, reflexivity_monitor=monitor,
            risk_agent=risk_agent, agents=agents,
        )

        engine.run()
        results = engine.get_results()

        assert "peak_manipulation_risk" in results
        assert "peak_bubble_risk" in results
        assert "high_risk_steps" in results
        assert results["steps"] == 10


# ── P1.4: ScenarioConfig ──────────────────────────────────────

class TestScenarioConfig:
    """P1.4: 验证 ScenarioConfig YAML 驱动实验"""

    def test_config_from_dict(self):
        """应能从字典创建配置"""
        from core.scenario_config import ScenarioConfig

        data = {
            "id": "test_01",
            "name": "test_scenario",
            "steps": 50,
            "seed": 42,
            "market": {"initial_price": 100.0, "noise_std": 0.01},
            "regulation": {"mode": "none"},
            "narratives": [
                {"step": 10, "name": "test", "intensity": 0.7}
            ],
        }

        config = ScenarioConfig.from_dict(data)
        assert config.id == "test_01"
        assert config.steps == 50
        assert config.seed == 42
        assert config.market.initial_price == 100.0
        assert config.regulation.mode == "none"
        assert len(config.narratives) == 1
        assert config.narratives[0].step == 10

    def test_config_validate_results(self):
        """应能验证仿真结果"""
        from core.scenario_config import ScenarioConfig, ExpectedMetrics

        config = ScenarioConfig(
            expected=ExpectedMetrics(
                bubble_risk_peak_min=0.15,
                high_risk_steps_max=30,
            )
        )

        results_pass = {"peak_bubble_risk": 0.20, "high_risk_steps": 25}
        checks = config.validate_results(results_pass)
        assert checks["bubble_risk_peak_min"] is True
        assert checks["high_risk_steps_max"] is True

        results_fail = {"peak_bubble_risk": 0.10, "high_risk_steps": 35}
        checks = config.validate_results(results_fail)
        assert checks["bubble_risk_peak_min"] is False
        assert checks["high_risk_steps_max"] is False

    def test_yaml_scenario_exists(self):
        """YAML 场景文件应存在且可加载"""
        from core.scenario_config import ScenarioConfig

        yaml_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "scenarios", "E01_regulation_baseline.yaml"
        )
        assert os.path.exists(yaml_path)

        config = ScenarioConfig.from_yaml(yaml_path)
        assert config.id == "E01"
        assert config.regulation.mode == "none"
        assert len(config.narratives) == 5
