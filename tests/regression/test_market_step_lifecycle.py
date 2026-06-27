"""
tests/regression/test_market_step_lifecycle.py
================================================
PR-1 回归测试：验证 MarketEnvironment step 生命周期

核心断言：
- 无订单 step 不得继承上一轮 net_demand
- step_net_demand 每步重置
- cumulative_net_demand 只增不减（供报告用）
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField


def test_begin_step_resets_volumes():
    """begin_step() 必须清零当步交易量"""
    market = MarketEnvironment(initial_price=100.0)
    emotion = EmotionField()

    # Step 1: 有买入订单
    market.begin_step()
    market.submit_order("agent_1", "BUY", 10.0)
    market.submit_order("agent_2", "SELL", 5.0)
    market.update_price(emotion)

    assert market.step_buy_volume == 10.0, f"Expected 10.0, got {market.step_buy_volume}"
    assert market.step_sell_volume == 5.0, f"Expected 5.0, got {market.step_sell_volume}"
    assert market.net_demand == 5.0, f"Expected net_demand=5.0, got {market.net_demand}"

    # Step 2: 无订单 → begin_step 清零
    market.begin_step()
    assert market.step_buy_volume == 0.0, f"Expected 0.0 after begin_step, got {market.step_buy_volume}"
    assert market.step_sell_volume == 0.0, f"Expected 0.0 after begin_step, got {market.step_sell_volume}"
    assert market.net_demand == 0.0, f"Expected net_demand=0.0 after begin_step, got {market.net_demand}"


def test_no_order_step_no_inherited_demand():
    """无订单 step 不得继承上一轮 net_demand"""
    market = MarketEnvironment(initial_price=100.0)
    emotion = EmotionField()

    # Step 1: 大量买入
    market.begin_step()
    market.submit_order("agent_1", "BUY", 50.0)
    market.update_price(emotion)
    step1_demand = market.net_demand
    assert step1_demand > 0, f"Step 1 should have positive net_demand, got {step1_demand}"

    # Step 2: 无订单 → net_demand 必须为 0
    market.begin_step()
    market.update_price(emotion)
    step2_demand = market.net_demand
    assert step2_demand == 0.0, f"Step 2 net_demand must be 0, got {step2_demand}"


def test_cumulative_net_demand_grows():
    """cumulative_net_demand 应跨步累积"""
    market = MarketEnvironment(initial_price=100.0)
    emotion = EmotionField()

    # Step 1
    market.begin_step()
    market.submit_order("agent_1", "BUY", 10.0)
    market.update_price(emotion)
    cum_after_step1 = market.cumulative_net_demand
    assert cum_after_step1 == 10.0, f"Expected 10.0, got {cum_after_step1}"

    # Step 2
    market.begin_step()
    market.submit_order("agent_2", "SELL", 3.0)
    market.update_price(emotion)
    cum_after_step2 = market.cumulative_net_demand
    assert cum_after_step2 == 7.0, f"Expected 7.0 (10-3), got {cum_after_step2}"

    # Step 3: 无订单
    market.begin_step()
    market.update_price(emotion)
    cum_after_step3 = market.cumulative_net_demand
    assert cum_after_step3 == 7.0, f"Expected 7.0 (unchanged), got {cum_after_step3}"


def test_order_imbalance_per_step():
    """order_imbalance 应只反映当步数据"""
    market = MarketEnvironment(initial_price=100.0)
    emotion = EmotionField()

    # Step 1: 全部买入
    market.begin_step()
    market.submit_order("agent_1", "BUY", 10.0)
    market.update_price(emotion)
    assert market.order_imbalance == 1.0, f"Expected 1.0, got {market.order_imbalance}"

    # Step 2: 无订单 → imbalance = 0
    market.begin_step()
    market.update_price(emotion)
    assert market.order_imbalance == 0.0, f"Expected 0.0, got {market.order_imbalance}"


def test_price_not_driven_by_stale_demand():
    """价格不应因上一轮 net_demand 残留而继续变化（在无新订单时）"""
    market = MarketEnvironment(initial_price=100.0, impact_coefficient=0.5)
    emotion = EmotionField(greed=0.5, fear=0.3)

    # Step 1: 大量买入推高价格
    market.begin_step()
    market.submit_order("agent_1", "BUY", 30.0)
    market.update_price(emotion)
    price_after_step1 = market.price

    # Step 2: 无订单 → 价格应只受噪声和均值回复影响
    # 不应该像 Step 1 那样大幅上涨
    market.begin_step()
    market.update_price(emotion)
    price_after_step2 = market.price

    # 由于 net_demand=0, order_imbalance=0, 价格变化仅来自噪声和均值回复
    # 连续多步无订单后价格应趋向基本面
    for _ in range(50):
        market.begin_step()
        market.update_price(emotion)

    price_after_50_idle = market.price
    # 价格应回到基本面附近（100），不应持续偏离
    assert abs(price_after_50_idle - 100.0) < 15.0, \
        f"Price should revert toward fundamental, got {price_after_50_idle}"


if __name__ == "__main__":
    test_begin_step_resets_volumes()
    test_no_order_step_no_inherited_demand()
    test_cumulative_net_demand_grows()
    test_order_imbalance_per_step()
    test_price_not_driven_by_stale_demand()
    print("[PASS] All test_market_step_lifecycle tests passed!")
