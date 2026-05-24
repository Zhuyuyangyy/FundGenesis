"""
experiments/emotion_shock.py
============================
实验1：情绪冲击实验
固定基本面不变，只改变情绪场初始状态
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.creator_controller import CreatorController, MarketConfig, ShockConfig
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from core.metrics import MarketMetrics
from agents.base_agent import AgentConfig
from agents.value_investor import ValueInvestor
from agents.trend_follower import TrendFollower
from agents.emotional_retail import EmotionalRetail
from reflexivity.belief_updater import update_agent_beliefs, compute_market_herding_pressure


def build_society(total: int = 100) -> list:
    """构建 Agent 社会"""
    agents = []
    n_value = int(total * 0.10)
    n_trend = int(total * 0.30)
    n_retail = total - n_value - n_trend

    for i in range(n_value):
        agents.append(ValueInvestor(f"V{i}", fair_value=100.0))
    for i in range(n_trend):
        agents.append(TrendFollower(f"T{i}"))
    for i in range(n_retail):
        agents.append(EmotionalRetail(f"R{i}"))
    return agents


def run_single_scenario(scenario_name: str, emotion_config: dict,
                        shock: ShockConfig = None, steps: int = 500,
                        seed: int = 42) -> dict:
    """运行单个场景"""
    np.random.seed(seed)

    # 初始化
    controller = CreatorController(
        market_config=MarketConfig(),
        emotion_config=emotion_config,
        shocks=[shock] if shock else [],
    )

    market = controller.setup_market()
    emotion = controller.setup_emotion()
    agents = build_society()

    price_log = []
    emotion_log = []
    metrics_log = []

    for step in range(steps):
        # 检查冲击注入
        injected = controller.check_and_inject_shock(step, market, emotion)
        if injected:
            print(f"  [Shock @ step {step}] {injected.shock_description}")

        # 重置交易量
        market.reset_volumes()

        # Agent 决策
        for agent in agents:
            action = agent.decide(market, emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)

        # 更新价格
        market.update_price(emotion)

        # 情绪受价格变化驱动
        emotion.apply_price_change(market.price_change_pct)
        emotion.decay_toward_neutral(inertia=emotion_config.get("fear_inertia", 0.95))

        # 信念更新（反身性）
        herding = compute_market_herding_pressure(agents)
        update_agent_beliefs(agents, market, emotion, herding_pressure=herding)

        # 记录
        price_log.append(market.price)
        emotion_log.append(emotion.to_vector())

        m = market.get_metrics(emotion, step)
        metrics_log.append({
            "step": step,
            "price": market.price,
            "return": m.cumulative_return,
            "volatility": m.volatility,
            "order_imbalance": m.order_imbalance,
            "bubble": m.bubble_indicator,
            "fear_greed": m.fear_greed_index,
        })

    return {
        "scenario": scenario_name,
        "price_log": price_log,
        "emotion_log": emotion_log,
        "metrics_log": metrics_log,
        "final_price": price_log[-1] if price_log else 0,
        "max_price": max(price_log) if price_log else 0,
        "min_price": min(price_log) if price_log else 0,
        "volatility": np.std(market.returns_history[-100:]) if len(market.returns_history) >= 100 else 0,
    }


def run_emotion_shock_experiment(output_dir: str = "outputs"):
    """
    情绪冲击实验主函数。
    四组场景：neutral / greed / panic / greed_to_panic
    """
    os.makedirs(output_dir, exist_ok=True)

    scenarios = {
        "neutral": {
            "initial_fear": 0.3, "initial_greed": 0.3,
            "fear_inertia": 0.95, "greed_inertia": 0.95,
        },
        "greed": {
            "initial_fear": 0.1, "initial_greed": 0.8,
            "fear_inertia": 0.95, "greed_inertia": 0.98,
        },
        "panic": {
            "initial_fear": 0.9, "initial_greed": 0.1,
            "fear_inertia": 0.98, "greed_inertia": 0.95,
        },
        "greed_to_panic": {
            "initial_fear": 0.1, "initial_greed": 0.8,
            "fear_inertia": 0.95, "greed_inertia": 0.98,
        },
    }

    shock_greed_to_panic = ShockConfig(
        shock_type="news",
        shock_magnitude=-0.35,
        shock_timing=250,
        shock_description="负面新闻冲击：从贪婪快速切换至恐慌",
    )

    results = {}

    print("=" * 60)
    print("FundGenesis 实验1：情绪冲击实验")
    print("=" * 60)

    for name, cfg in scenarios.items():
        shock = shock_greed_to_panic if name == "greed_to_panic" else None
        print(f"\n[RUN] 场景：{name} | 初始情绪：fear={cfg['initial_fear']}, greed={cfg['initial_greed']}")
        if shock:
            print(f"  冲击：第{shock.shock_timing}步注入，magnitude={shock.shock_magnitude}")

        result = run_single_scenario(name, cfg, shock=shock, steps=500)
        results[name] = result

        print(f"  最终价格：{result['final_price']:.2f} | "
              f"最高：{result['max_price']:.2f} | "
              f"波动率：{result['volatility']:.4f}")

    # 绘图：价格曲线
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    colors = {"neutral": "#4CAF50", "greed": "#FF9800",
               "panic": "#F44336", "greed_to_panic": "#9C27B0"}

    for ax, (name, res) in zip(axes, results.items()):
        price_log = res["price_log"]
        steps = range(len(price_log))
        ax.plot(steps, price_log, color=colors[name], linewidth=1.5)
        ax.axhline(y=100.0, color="gray", linestyle="--", alpha=0.5, label="initial")
        ax.set_title(f"{name.upper()}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Step")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.3)
        ax.legend()

    plt.suptitle("FundGenesis Experiment 1: Emotion Shock\nPrice Trajectories", fontsize=14)
    plt.tight_layout()
    price_path = os.path.join(output_dir, "emotion_shock_price.png")
    plt.savefig(price_path, dpi=150)
    plt.close()
    print(f"\n[OK] 价格曲线已保存：{price_path}")

    # 绘图：情绪演变
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for ax, (name, res) in zip(axes, results.items()):
        emotion_log = np.array(res["emotion_log"])
        steps = range(len(emotion_log))
        labels = ["fear", "greed", "confidence", "uncertainty"]
        for i, label in enumerate(labels):
            ax.plot(steps, emotion_log[:, i], label=label, linewidth=1.2)
        ax.set_title(f"{name.upper()}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Step")
        ax.set_ylabel("Intensity")
        ax.set_ylim(0, 1)
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.suptitle("Emotion Field Evolution", fontsize=14)
    plt.tight_layout()
    emotion_path = os.path.join(output_dir, "emotion_shock_emotion.png")
    plt.savefig(emotion_path, dpi=150)
    plt.close()
    print(f"[OK] 情绪曲线已保存：{emotion_path}")

    # 保存数据
    summary = {}
    for name, res in results.items():
        summary[name] = {
            "final_price": round(res["final_price"], 4),
            "max_price": round(res["max_price"], 4),
            "min_price": round(res["min_price"], 4),
            "volatility": round(res["volatility"], 6),
        }

    summary_path = os.path.join(output_dir, "emotion_shock_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"experiment": "emotion_shock", "results": summary}, f, indent=2)
    print(f"[OK] 汇总数据已保存：{summary_path}")

    return results


if __name__ == "__main__":
    run_emotion_shock_experiment()
