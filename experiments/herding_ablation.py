"""
experiments/herding_ablation.py
================================
实验2：羊群效应消融实验
控制羊群系数从 0.0 到 0.9，观察市场行为变化
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.creator_controller import CreatorController, MarketConfig
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from agents.base_agent import AgentConfig
from agents.value_investor import ValueInvestor
from agents.trend_follower import TrendFollower
from agents.emotional_retail import EmotionalRetail
from reflexivity.belief_updater import update_agent_beliefs, compute_market_herding_pressure


def build_society(total: int, retail_herding: float) -> list:
    agents = []
    n_value = int(total * 0.10)
    n_trend = int(total * 0.30)
    n_retail = total - n_value - n_trend

    for i in range(n_value):
        cfg = AgentConfig(herding_coefficient=0.1)
        agents.append(ValueInvestor(f"V{i}", fair_value=100.0, config=cfg))
    for i in range(n_trend):
        cfg = AgentConfig(herding_coefficient=0.4)
        agents.append(TrendFollower(f"T{i}", config=cfg))
    for i in range(n_retail):
        cfg = AgentConfig(herding_coefficient=retail_herding)
        agents.append(EmotionalRetail(f"R{i}", config=cfg))
    return agents


def run_herding_experiment(output_dir: str = "outputs", steps: int = 500):
    os.makedirs(output_dir, exist_ok=True)

    herding_levels = [0.0, 0.3, 0.6, 0.9]
    results = {}

    print("=" * 60)
    print("FundGenesis 实验2：羊群效应消融实验")
    print("=" * 60)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(herding_levels)))

    for idx, herding in enumerate(herding_levels):
        print(f"\n[RUN] 羊群系数 H = {herding}")

        np.random.seed(42)
        emotion_cfg = {"initial_fear": 0.3, "initial_greed": 0.5,
                       "fear_inertia": 0.95, "greed_inertia": 0.95}
        controller = CreatorController(
            market_config=MarketConfig(),
            emotion_config=emotion_cfg,
        )
        market = controller.setup_market()
        emotion = controller.setup_emotion()
        agents = build_society(100, herding)

        price_log = []
        volatility_log = []

        for step in range(steps):
            market.reset_volumes()
            for agent in agents:
                action = agent.decide(market, emotion)
                market.submit_order(agent.agent_id, action.value, agent.get_trade_volume())

            market.update_price(emotion)
            emotion.apply_price_change(market.price_change_pct)
            emotion.decay_toward_neutral()

            herding_pressure = compute_market_herding_pressure(agents)
            update_agent_beliefs(agents, market, emotion, herding_pressure)

            price_log.append(market.price)
            volatility_log.append(market.get_volatility())

        ax = axes[idx]
        ax.plot(price_log, color=colors[idx], linewidth=1.5)
        ax.axhline(y=100.0, color="gray", linestyle="--", alpha=0.5)
        ax.set_title(f"Herding H = {herding}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Step")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.3)

        final_ret = (price_log[-1] - 100.0) / 100.0
        max_price = max(price_log)
        max_vol = max(volatility_log)
        print(f"  最终收益：{final_ret*100:.1f}% | 最高价格：{max_price:.2f} | 最大波动：{max_vol:.4f}")

        results[herding] = {
            "price_log": price_log,
            "final_return": final_ret,
            "max_price": max_price,
            "volatility": np.std(market.returns_history[-100:]) if len(market.returns_history) >= 100 else 0,
        }

    plt.suptitle("FundGenesis Experiment 2: Herding Ablation\nPrice Trajectories", fontsize=14)
    plt.tight_layout()
    path = os.path.join(output_dir, "herding_ablation.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"\n[OK] 图表已保存：{path}")

    summary_path = os.path.join(output_dir, "herding_ablation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"experiment": "herding_ablation", "results": {
            str(k): {kk: round(vv, 6) for kk, vv in v.items() if kk != "price_log"}
            for k, v in results.items()
        }}, f, indent=2)
    print(f"[OK] 汇总已保存：{summary_path}")

    return results


if __name__ == "__main__":
    run_herding_experiment()
