"""
experiments/black_swan.py
=========================
实验3：黑天鹅冲击实验
在市场稳定后注入负面冲击，观察不同情绪场下的恢复模式
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.creator_controller import CreatorController, MarketConfig, ShockConfig
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from agents.base_agent import AgentConfig
from agents.value_investor import ValueInvestor
from agents.trend_follower import TrendFollower
from agents.emotional_retail import EmotionalRetail
from reflexivity.belief_updater import update_agent_beliefs, compute_market_herding_pressure


def build_society(total: int = 100) -> list:
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


def run_single_blackswan(emotion_initial: dict, shock_step: int = 300,
                          shock_mag: float = -0.40, steps: int = 600) -> dict:
    np.random.seed(42)
    controller = CreatorController(
        market_config=MarketConfig(),
        emotion_config=emotion_initial,
        shocks=[ShockConfig(
            shock_type="black_swan",
            shock_magnitude=shock_mag,
            shock_timing=shock_step,
            shock_description=f"黑天鹅冲击 @ step {shock_step}",
        )]
    )
    market = controller.setup_market()
    emotion = controller.setup_emotion()
    agents = build_society()

    price_log = []
    emotion_log = []

    for step in range(steps):
        controller.check_and_inject_shock(step, market, emotion)
        market.reset_volumes()
        for agent in agents:
            action = agent.decide(market, emotion)
            market.submit_order(agent.agent_id, action.value, agent.get_trade_volume())
        market.update_price(emotion)
        emotion.apply_price_change(market.price_change_pct)
        emotion.decay_toward_neutral()
        update_agent_beliefs(agents, market, emotion,
                             herding_pressure=compute_market_herding_pressure(agents))
        price_log.append(market.price)
        emotion_log.append(emotion.to_vector())

    return {
        "price_log": price_log,
        "emotion_log": emotion_log,
        "pre_shock_price": price_log[shock_step - 1] if shock_step < len(price_log) else price_log[0],
        "post_shock_trough": min(price_log[shock_step:shock_step + 50]),
        "final_price": price_log[-1],
    }


def run_black_swan_experiment(output_dir: str = "outputs"):
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("FundGenesis 实验3：黑天鹅冲击实验")
    print("=" * 60)

    scenarios = {
        "resilient": {"initial_fear": 0.2, "initial_greed": 0.3,
                      "fear_inertia": 0.9, "greed_inertia": 0.9},
        "normal":    {"initial_fear": 0.4, "initial_greed": 0.4,
                      "fear_inertia": 0.95, "greed_inertia": 0.95},
        "fragile":   {"initial_fear": 0.8, "initial_greed": 0.6,
                      "fear_inertia": 0.98, "greed_inertia": 0.98},
    }

    results = {}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    colors = {"resilient": "#4CAF50", "normal": "#FF9800", "fragile": "#F44336"}
    shock_step = 300

    for (name, cfg), ax in zip(scenarios.items(), axes):
        print(f"\n[RUN] 场景：{name} | fear={cfg['initial_fear']}, greed={cfg['initial_greed']}")
        res = run_single_blackswan(cfg, shock_step=shock_step)
        results[name] = res

        price_log = res["price_log"]
        ax.plot(price_log, color=colors[name], linewidth=1.5)
        ax.axvline(x=shock_step, color="red", linestyle="--", alpha=0.7,
                   label=f"Shock @ {shock_step}")
        ax.axhline(y=100.0, color="gray", linestyle="--", alpha=0.4)
        ax.set_title(f"{name.upper()}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Step")
        ax.set_ylabel("Price")
        ax.legend()
        ax.grid(True, alpha=0.3)

        drop = (res["post_shock_trough"] - res["pre_shock_price"]) / res["pre_shock_price"]
        recovery = (res["final_price"] - res["post_shock_trough"]) / res["post_shock_trough"]
        print(f"  冲击前价格：{res['pre_shock_price']:.2f} | "
              f"冲击后最低：{res['post_shock_trough']:.2f} ({drop*100:.1f}%) | "
              f"最终价格：{res['final_price']:.2f} | "
              f"反弹幅度：{recovery*100:.1f}%")

    plt.suptitle("FundGenesis Experiment 3: Black Swan Shock\nMarket Fragility Comparison", fontsize=14)
    plt.tight_layout()
    path = os.path.join(output_dir, "black_swan.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"\n[OK] 图表已保存：{path}")

    summary_path = os.path.join(output_dir, "black_swan_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"experiment": "black_swan", "shock_step": shock_step,
                    "results": {k: {
                        "pre_shock_price": round(v["pre_shock_price"], 4),
                        "post_shock_trough": round(v["post_shock_trough"], 4),
                        "final_price": round(v["final_price"], 4),
                    } for k, v in results.items()}}, f, indent=2)
    print(f"[OK] 汇总已保存：{summary_path}")

    return results


if __name__ == "__main__":
    run_black_swan_experiment()
