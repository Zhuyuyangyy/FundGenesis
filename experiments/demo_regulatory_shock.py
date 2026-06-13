"""
experiments/demo_regulatory_shock.py
=====================================
Demo 2?????????

???
  ?????? ? KOL???? ? ?????? ?
  ?????? ? ?? ? ???? ?
  ???????

?????
  - uncertainty ????
  - fear ???greed ??
  - price ?????????
  - panic_risk_score ??
  - reflexivity_index ??????
"""

import os
import sys
import json
import logging
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger('FundGenesis.experiments.regulatory_shock')

from core.creator_controller import CreatorController, MarketConfig
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor
from agents.emotional_retail import EmotionalRetailAgent
from agents.trend_follower import TrendFollowerAgent
from agents.value_investor import ValueInvestorAgent


def run_demo_regulatory_shock(output_dir: str = None, steps: int = 300):
    """????????Demo"""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs"
        )
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Starting Demo 2: Regulatory Shock - Panic Diffusion")
    print("=" * 60)
    print("Demo 2: Regulatory Shock -- Panic Diffusion")
    print("=" * 60)

    # --- ????????????????????????---
    controller = CreatorController(
        market_config=MarketConfig(
            initial_price=120.0,      # ???????????
            impact_coefficient=0.12,
            noise_std=0.008,
            total_agents=100,
        ),
        emotion_config={
            "initial_fear": 0.15,
            "initial_greed": 0.6,     # ??????????
            "fear_inertia": 0.92,
            "greed_inertia": 0.92,
        }
    )

    market = controller.setup_market()
    emotion = controller.setup_emotion()
    belief_updater = BeliefUpdaterV2()

    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )
    narrative_engine = NarrativeEngine()
    propagator = PropagationModel(kol_network)
    monitor = ReflexivityMonitor()

    # --- Agent ?? ---
    agents = []
    for i in range(100):
        if i < 10:
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        elif i < 40:
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        else:
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

    # --- ????????????????---
    for step in range(50):
        for agent in agents:
            action = agent.decide(market.get_snapshot(), emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)
        market.update_price(emotion)
        emotion.decay_toward_neutral(inertia=0.9)

    pre_shock_price = market.price
    print(f"Pre-shock price (after buildup): {pre_shock_price:.2f}")

    price_history = []
    emotion_history = []
    metrics_history = []

    SHOCK_INJECTION_STEP = 80

    for step in range(steps):
        # ??????
        if step == SHOCK_INJECTION_STEP:
            narrative = NarrativeEvent(
                name="??????AI????",
                category=NarrativeCategory.REGULATORY,
                polarity=Polarity.NEGATIVE,
                target_sector="healthcare_ai",
                intensity=0.8,
                credibility=0.75,
                novelty=0.9,
                duration=60,
                source="MacroKOL",
            )
            narrative_engine.inject(narrative)
            propagator.inject_narrative(narrative)
            logger.info(f"Step {step}: Regulatory shock narrative injected - {narrative.name}")
            print(f"\n[Step {step}]  Narrative injected: {narrative.name}")
            print(f"    polarity={narrative.polarity.value}, intensity={narrative.intensity}")

        # --- ???? ---
        propagator.step()
        narrative_engine.tick()

        belief_updater.update_all(
            agents=agents, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine,
        )

        price_change = market.price_change_pct if market.price_history else 0.0
        narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)

        for agent in agents:
            action = agent.decide(market.get_snapshot(), emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)

        market.update_price(emotion)
        emotion.decay_toward_neutral(inertia=0.88)

        metrics = monitor.observe(
            step=step, market=market, emotion=emotion,
            kol_network=kol_network, narrative_engine=narrative_engine,
            agents=agents,
        )
        metrics_history.append(metrics.as_dict())

        price_history.append(market.price)
        emotion_history.append({
            "fear": emotion.fear,
            "greed": emotion.greed,
            "fg_index": emotion.fear_greed_index,
            "uncertainty": emotion.uncertainty,
        })

        if step % 30 == 0:
            logger.debug(f"Step {step}: Price={market.price:.2f}, Fear={emotion.fear:.3f}, Uncertainty={emotion.uncertainty:.3f}, RefIdx={metrics.reflexivity_index:.3f}, Panic={metrics.panic_risk_score:.3f}")
            print(f"  Step {step:3d} | Price: {market.price:7.2f} | "
                  f"Fear: {emotion.fear:.3f} | Uncertainty: {emotion.uncertainty:.3f} | "
                  f"RefIdx: {metrics.reflexivity_index:.3f} | "
                  f"Panic: {metrics.panic_risk_score:.3f}")

    # --- ??? ---
    _plot_regulatory_shock_results(
        price_history, emotion_history, metrics_history, SHOCK_INJECTION_STEP,
        pre_shock_price, output_dir
    )

    final_metrics = metrics_history[-1]
    result = {
        "demo": "regulatory_shock_panic",
        "description": "????????",
        "pre_shock_price": round(pre_shock_price, 2),
        "final_price": round(price_history[-1], 2),
        "price_change_pct": round((price_history[-1] - pre_shock_price) / pre_shock_price, 4),
        "final_panic_risk": final_metrics["panic_risk_score"],
        "peak_panic_risk": round(max(m["panic_risk_score"] for m in metrics_history), 4),
        "final_reflexivity_index": final_metrics["reflexivity_index"],
        "regime_distribution": monitor.regime_summary(),
    }

    result_path = os.path.join(output_dir, "demo_regulatory_shock_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Demo 2 completed: final_price={result['final_price']}, panic_risk={result['final_panic_risk']}")
    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"\n? Results saved to: {output_dir}/")

    return result


def _plot_regulatory_shock_results(price_history, emotion_history, metrics_history,
                                    shock_step, pre_shock_price, output_dir):
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    steps = range(len(price_history))

    ax = axes[0]
    ax.plot(steps, price_history, 'b-', linewidth=1.5, label="Price")
    ax.axvline(x=shock_step, color='red', linestyle='--', alpha=0.8, label="Regulatory Shock")
    ax.axhline(y=pre_shock_price, color='gray', linestyle=':', alpha=0.5)
    ax.set_title("Demo 2: Price Path -- Regulatory Shock & Panic", fontsize=12)
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[1]
    fear = [e["fear"] for e in emotion_history]
    uncertainty = [e["uncertainty"] for e in emotion_history]
    ax.plot(steps, fear, 'r-', linewidth=1.5, label="Fear")
    ax.plot(steps, uncertainty, 'orange', linewidth=1.5, label="Uncertainty")
    ax.axvline(x=shock_step, color='red', linestyle='--', alpha=0.8)
    ax.set_title("Fear & Uncertainty Spike")
    ax.set_ylabel("Index")
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[2]
    ref_idx = [m["reflexivity_index"] for m in metrics_history]
    panic = [m["panic_risk_score"] for m in metrics_history]
    ax.plot(steps, ref_idx, 'b-', linewidth=1.5, label="Reflexivity Index")
    ax.plot(steps, panic, 'r-', linewidth=1.5, label="Panic Risk Score")
    ax.axhline(y=0.6, color='orange', linestyle=':', alpha=0.7)
    ax.axvline(x=shock_step, color='red', linestyle='--', alpha=0.8)
    ax.set_title("Reflexivity Index & Panic Risk")
    ax.set_xlabel("Step")
    ax.set_ylabel("Score")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "demo_regulatory_shock.png")
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f" Chart saved: {fig_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    run_demo_regulatory_shock(output_dir=args.output, steps=args.steps)
