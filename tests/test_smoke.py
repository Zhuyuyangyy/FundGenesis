"""
test_smoke.py - 冒烟测试
========================

验证项目的基本导入和配置是否正确。
这些测试应该始终通过，失败意味着项目有严重问题。
"""

import sys
import os
import pytest


# ── 导入测试 ────────────────────────────────────────────────────

class TestImports:
    """测试所有核心模块是否可以正常导入"""

    def test_import_core_market_environment(self):
        """core.market_environment 应该可以正常导入"""
        from core.market_environment import MarketEnvironment, MarketSnapshot
        assert MarketEnvironment is not None
        assert MarketSnapshot is not None

    def test_import_core_emotion_field(self):
        """core.emotion_field 应该可以正常导入"""
        from core.emotion_field import EmotionField
        assert EmotionField is not None

    def test_import_core_creator_controller(self):
        """core.creator_controller 应该可以正常导入"""
        from core.creator_controller import CreatorController, MarketConfig, ShockConfig
        assert CreatorController is not None
        assert MarketConfig is not None
        assert ShockConfig is not None

    def test_import_core_metrics(self):
        """core.metrics 应该可以正常导入"""
        from core.metrics import MarketMetrics
        assert MarketMetrics is not None

    def test_import_agents_base(self):
        """agents.base_agent 应该可以正常导入"""
        from agents.base_agent import BaseAgent, Action, AgentConfig
        assert BaseAgent is not None
        assert Action is not None
        assert AgentConfig is not None

    def test_import_agents_emotional_retail(self):
        """agents.emotional_retail 应该可以正常导入"""
        from agents.emotional_retail import EmotionalRetail, EmotionalRetailAgent
        assert EmotionalRetail is not None
        assert EmotionalRetailAgent is not None

    def test_import_agents_trend_follower(self):
        """agents.trend_follower 应该可以正常导入"""
        from agents.trend_follower import TrendFollower, TrendFollowerAgent
        assert TrendFollower is not None
        assert TrendFollowerAgent is not None

    def test_import_agents_value_investor(self):
        """agents.value_investor 应该可以正常导入"""
        from agents.value_investor import ValueInvestor, ValueInvestorAgent
        assert ValueInvestor is not None
        assert ValueInvestorAgent is not None

    def test_import_social_kol_network(self):
        """social.kol_network 应该可以正常导入"""
        from social.kol_network import KOLNetwork, KOLNode, KOLTier
        assert KOLNetwork is not None
        assert KOLNode is not None
        assert KOLTier is not None

    def test_import_trust_engine(self):
        """trust.trust_engine 应该可以正常导入"""
        from trust.trust_engine import TrustEngine, TrustConfig, KOLTrustState
        assert TrustEngine is not None
        assert TrustConfig is not None
        assert KOLTrustState is not None

    def test_import_narrative_engine(self):
        """narrative.narrative_engine 应该可以正常导入"""
        from narrative.narrative_engine import NarrativeEngine, NarrativeEngineConfig
        assert NarrativeEngine is not None
        assert NarrativeEngineConfig is not None

    def test_import_narrative_event(self):
        """narrative.narrative_event 应该可以正常导入"""
        from narrative.narrative_event import NarrativeEvent, NarrativeRegistry, Polarity
        assert NarrativeEvent is not None
        assert NarrativeRegistry is not None
        assert Polarity is not None

    def test_import_risk_modules(self):
        """risk 模块应该可以正常导入"""
        from risk.manipulation_risk_agent import ManipulationRiskAgent
        from risk.regulator_agent import RegulatorAgent
        assert ManipulationRiskAgent is not None
        assert RegulatorAgent is not None

    def test_import_monitor(self):
        """monitor 模块应该可以正常导入"""
        from monitor.reflexivity_monitor import ReflexivityMonitor
        assert ReflexivityMonitor is not None

    def test_import_core_init(self):
        """core.__init__ 应该导出核心类"""
        from core import MarketEnvironment, EmotionField, CreatorController
        assert MarketEnvironment is not None
        assert EmotionField is not None
        assert CreatorController is not None


# ── 配置测试 ────────────────────────────────────────────────────

class TestConfiguration:
    """测试默认配置是否合理"""

    def test_market_config_defaults(self):
        """MarketConfig 默认值应该合理"""
        from core.creator_controller import MarketConfig
        cfg = MarketConfig()
        assert cfg.initial_price > 0
        assert cfg.impact_coefficient > 0
        assert cfg.noise_std > 0
        assert cfg.total_agents > 0

    def test_agent_config_defaults(self):
        """AgentConfig 默认值应该合理"""
        from agents.base_agent import AgentConfig
        cfg = AgentConfig()
        assert cfg.cash > 0
        assert cfg.position >= 0
        assert -1 <= cfg.belief <= 1
        assert 0 <= cfg.herding_coefficient <= 1
        assert 0 <= cfg.emotional_sensitivity <= 1

    def test_trust_config_defaults(self):
        """TrustConfig 默认值应该合理"""
        from trust.trust_engine import TrustConfig
        cfg = TrustConfig()
        assert 0 < cfg.credibility_alpha <= 1
        assert 0 < cfg.social_proof_beta <= 1
        assert 0 < cfg.price_validation_gamma <= 1
        assert cfg.min_effective_trust > 0

    def test_narrative_engine_config_defaults(self):
        """NarrativeEngineConfig 默认值应该合理"""
        from narrative.narrative_engine import NarrativeEngineConfig
        cfg = NarrativeEngineConfig()
        assert 0 < cfg.belief_impact_coef <= 1
        assert 0 < cfg.emotion_impact_coef <= 1
        assert cfg.decay_rate > 0

    def test_emotion_field_defaults(self):
        """EmotionField 默认值应该在 [0, 1] 范围内"""
        from core.emotion_field import EmotionField
        ef = EmotionField()
        assert 0 <= ef.fear <= 1
        assert 0 <= ef.greed <= 1
        assert 0 <= ef.confidence <= 1
        assert 0 <= ef.uncertainty <= 1


# ── 项目结构测试 ────────────────────────────────────────────────

class TestProjectStructure:
    """测试项目目录结构是否完整"""

    def test_main_py_exists(self):
        """main.py 应该存在"""
        main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
        assert os.path.exists(main_path), "main.py not found"

    def test_requirements_txt_exists(self):
        """requirements.txt 应该存在"""
        req_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")
        assert os.path.exists(req_path), "requirements.txt not found"

    def test_core_directory_exists(self):
        """core/ 目录应该存在"""
        core_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core")
        assert os.path.isdir(core_path), "core/ directory not found"

    def test_agents_directory_exists(self):
        """agents/ 目录应该存在"""
        agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
        assert os.path.isdir(agents_path), "agents/ directory not found"

    def test_experiments_directory_exists(self):
        """experiments/ 目录应该存在"""
        exp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments")
        assert os.path.isdir(exp_path), "experiments/ directory not found"
