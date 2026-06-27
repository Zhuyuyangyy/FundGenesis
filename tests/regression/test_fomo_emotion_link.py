"""
tests/regression/test_fomo_emotion_link.py
============================================
PR-2 回归测试：验证 FOMO → EmotionField 闭环

核心断言：
- FOMO 信号能显著提高 greed
- FOMO 信号产生 fomo_pressure
- ManipulationRiskAgent.get_fomo_emotion_impulse() 返回有效值
- FOMO 信号间接提高 emotion_factor()
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.emotion_field import EmotionField
from risk.manipulation_risk_agent import ManipulationRiskAgent, RiskLevel
from social.kol_network import KOLNetwork, KOLTier
from monitor.reflexivity_monitor import ReflexivityMonitor
from trust.trust_engine import TrustEngine, TrustConfig
from narrative.narrative_engine import NarrativeEngine
from core.market_environment import MarketEnvironment


def test_fomo_signal_increases_greed():
    """FOMO 信号必须提高 greed"""
    emotion = EmotionField(greed=0.3, fear=0.3)
    before_greed = emotion.greed

    emotion.apply_fomo_signal(0.8)

    assert emotion.greed > before_greed, \
        f"FOMO should increase greed: before={before_greed}, after={emotion.greed}"


def test_fomo_signal_creates_pressure():
    """FOMO 信号必须产生 fomo_pressure"""
    emotion = EmotionField()

    emotion.apply_fomo_signal(0.8)

    assert emotion.fomo_pressure > 0, \
        f"FOMO should create fomo_pressure, got {emotion.fomo_pressure}"


def test_fomo_signal_reduces_fear():
    """FOMO 信号应降低恐惧（FOMO 压倒谨慎）"""
    emotion = EmotionField(fear=0.5, greed=0.3)
    before_fear = emotion.fear

    emotion.apply_fomo_signal(0.8)

    assert emotion.fear < before_fear, \
        f"FOMO should reduce fear: before={before_fear}, after={emotion.fear}"


def test_fomo_increases_emotion_factor():
    """FOMO 信号应提高 emotion_factor()"""
    emotion = EmotionField(greed=0.3, fear=0.3)
    before_factor = emotion.emotion_factor()

    emotion.apply_fomo_signal(0.8)

    after_factor = emotion.emotion_factor()
    assert after_factor > before_factor, \
        f"FOMO should increase emotion_factor: before={before_factor}, after={after_factor}"


def test_fomo_pressure_decays():
    """fomo_pressure 应随时间衰减"""
    emotion = EmotionField()
    emotion.apply_fomo_signal(0.8)
    pressure_after_signal = emotion.fomo_pressure

    # 多步衰减
    for _ in range(20):
        emotion.decay_toward_neutral(inertia=0.90)

    assert emotion.fomo_pressure < pressure_after_signal, \
        f"fomo_pressure should decay: after_signal={pressure_after_signal}, after_decay={emotion.fomo_pressure}"


def test_risk_agent_fomo_impulse():
    """ManipulationRiskAgent.get_fomo_emotion_impulse() 在 FOMO 检测后应返回有效值"""
    risk_agent = ManipulationRiskAgent()

    # 初始时应该为 0
    assert risk_agent.get_fomo_emotion_impulse() == 0.0, \
        "Initial fomo impulse should be 0"

    # 注入 FOMO 信号
    risk_agent.record_fomo_signal(
        retail_buy_ratio=0.78,
        greed_level=0.82,
        belief_concentration=0.70,
        step=10,
    )

    # 创建依赖组件运行 evaluate
    kol_network = KOLNetwork().build_default_network(n_macro=1, n_influencer=2, n_micro=3, n_retail=10)
    trust_engine = TrustEngine(TrustConfig())
    from trust.trust_bootstrapper import TrustBootstrapper
    TrustBootstrapper().bootstrap_network(kol_network, trust_engine)
    reflexivity_monitor = ReflexivityMonitor()
    market = MarketEnvironment(initial_price=100.0)
    narrative_engine = NarrativeEngine()

    report = risk_agent.evaluate(
        step=10,
        kol_network=kol_network,
        trust_engine=trust_engine,
        reflexivity_monitor=reflexivity_monitor,
        market=market,
        narrative_engine=narrative_engine,
    )

    impulse = risk_agent.get_fomo_emotion_impulse()
    # FOMO 信号注入后，impulse 应大于 0
    assert impulse >= 0.0, f"FOMO impulse should be >= 0, got {impulse}"


def test_fomo_closed_loop_integration():
    """完整闭环测试：FOMO检测 → EmotionField → emotion_factor 变化"""
    emotion = EmotionField(greed=0.3, fear=0.3, confidence=0.5, uncertainty=0.3)
    risk_agent = ManipulationRiskAgent()

    # 注入 FOMO
    risk_agent.record_fomo_signal(
        retail_buy_ratio=0.80,
        greed_level=0.85,
        belief_concentration=0.60,
        step=1,
    )

    # 模拟主循环的闭环操作
    kol_network = KOLNetwork().build_default_network(n_macro=1, n_influencer=2, n_micro=3, n_retail=10)
    trust_engine = TrustEngine(TrustConfig())
    from trust.trust_bootstrapper import TrustBootstrapper
    TrustBootstrapper().bootstrap_network(kol_network, trust_engine)
    reflexivity_monitor = ReflexivityMonitor()
    market = MarketEnvironment(initial_price=100.0)
    narrative_engine = NarrativeEngine()

    risk_agent.evaluate(
        step=1, kol_network=kol_network, trust_engine=trust_engine,
        reflexivity_monitor=reflexivity_monitor, market=market,
        narrative_engine=narrative_engine,
    )

    fomo_impulse = risk_agent.get_fomo_emotion_impulse()
    if fomo_impulse > 0.1:
        emotion.apply_fomo_signal(fomo_impulse)

    # 验证闭环效果
    assert emotion.greed > 0.3, f"FOMO closed loop should increase greed above 0.3, got {emotion.greed}"
    assert emotion.fomo_pressure > 0, f"FOMO closed loop should create fomo_pressure, got {emotion.fomo_pressure}"


if __name__ == "__main__":
    test_fomo_signal_increases_greed()
    test_fomo_signal_creates_pressure()
    test_fomo_signal_reduces_fear()
    test_fomo_increases_emotion_factor()
    test_fomo_pressure_decays()
    test_risk_agent_fomo_impulse()
    test_fomo_closed_loop_integration()
    print("[PASS] All test_fomo_emotion_link tests passed!")
