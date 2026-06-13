"""
conftest.py - 共享测试 fixtures
================================

提供所有测试模块共用的 fixtures，避免重复代码。
"""

import sys
import os
import pytest

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── 核心对象 Fixtures ──────────────────────────────────────────

@pytest.fixture
def market():
    """创建一个干净的 MarketEnvironment 实例"""
    from core.market_environment import MarketEnvironment
    m = MarketEnvironment()
    m.reset(initial_price=100.0, impact_coefficient=0.5, noise_std=0.01, total_agents=100)
    return m


@pytest.fixture
def emotion():
    """创建一个中性 EmotionField 实例"""
    from core.emotion_field import EmotionField
    return EmotionField(fear=0.3, greed=0.3, confidence=0.5, uncertainty=0.3)


@pytest.fixture
def creator():
    """创建一个默认 CreatorController 实例"""
    from core.creator_controller import CreatorController, MarketConfig
    return CreatorController(
        market_config=MarketConfig(
            initial_price=100.0,
            impact_coefficient=0.15,
            noise_std=0.01,
            total_agents=100,
        )
    )


@pytest.fixture
def market_snapshot(market):
    """创建一个 MarketSnapshot 实例"""
    return market.get_snapshot()


# ── Agent Fixtures ──────────────────────────────────────────────

@pytest.fixture
def emotional_retail_agent():
    """创建一个 EmotionalRetail Agent"""
    from agents.emotional_retail import EmotionalRetail
    return EmotionalRetail("retail_001", fomo_sensitivity=1.5, panic_sensitivity=2.0)


@pytest.fixture
def trend_follower_agent():
    """创建一个 TrendFollower Agent"""
    from agents.trend_follower import TrendFollower
    return TrendFollower("trend_001", momentum_weight=3.0)


@pytest.fixture
def value_investor_agent():
    """创建一个 ValueInvestor Agent"""
    from agents.value_investor import ValueInvestor
    return ValueInvestor("value_001", fair_value=100.0, sensitivity=2.0)


# ── 社会网络 Fixtures ──────────────────────────────────────────

@pytest.fixture
def kol_network():
    """创建一个小型 KOL 网络用于测试"""
    from social.kol_network import KOLNetwork
    network = KOLNetwork()
    network.build_default_network(n_macro=1, n_influencer=2, n_micro=3, n_retail=10)
    return network


@pytest.fixture
def trust_engine():
    """创建一个 TrustEngine 实例"""
    from trust.trust_engine import TrustEngine
    return TrustEngine()


@pytest.fixture
def narrative_engine():
    """创建一个 NarrativeEngine 实例"""
    from narrative.narrative_engine import NarrativeEngine
    return NarrativeEngine()


@pytest.fixture
def agents():
    """创建一个 Agent 列表用于测试"""
    from agents.emotional_retail import EmotionalRetail
    from agents.trend_follower import TrendFollower
    from agents.value_investor import ValueInvestor
    agents_list = [
        EmotionalRetail("retail_001", fomo_sensitivity=1.5, panic_sensitivity=2.0),
        EmotionalRetail("retail_002", fomo_sensitivity=1.2, panic_sensitivity=1.8),
        TrendFollower("trend_001", momentum_weight=3.0),
        TrendFollower("trend_002", momentum_weight=2.5),
        ValueInvestor("value_001", fair_value=100.0, sensitivity=2.0),
    ]
    return agents_list


# ── 工具 Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_price_history():
    """生成一个样本价格序列"""
    import numpy as np
    np.random.seed(42)
    prices = [100.0]
    for _ in range(99):
        ret = np.random.normal(0.001, 0.02)
        prices.append(prices[-1] * (1 + ret))
    return prices


@pytest.fixture
def sample_returns():
    """生成一个样本收益率序列"""
    import numpy as np
    np.random.seed(42)
    return list(np.random.normal(0.001, 0.02, 100))
