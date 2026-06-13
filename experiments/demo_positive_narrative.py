"""
experiments/demo_positive_narrative.py
=======================================
Demo 1?????????

???
  AI?????? ? KOL?? ? ?????? ?
  ?????? ? ???? ? ???? ?
  ??????? ? ????

?????
  - narrative_penetration ????
  - belief_concentration ??????AI???
  - greed ???fear ??
  - reflexivity_index ?? 0.6
  - bubble_risk_score ????
  - ??????????
"""

import os
import sys
import json
import logging
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger('FundGenesis.experiments.positive_narrative')

from core.creator_controller import CreatorController, MarketConfig, ShockConfig
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor


def run_demo_positive_narrative(output_dir: str = None, steps: int = 300):
    """????????Demo"""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs"
        )
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Starting Demo 1: Positive Narrative Bubble Formation")
    print("=" * 60)
    print("Demo 1: Positive Narrative Bubble Formation")
    print("=" * 60)

    # --- ??? ---
    controller = CreatorController(
        market_config=MarketConfig(
            initial_price=100.0,
            impact_coefficient=0.20,
            noise_std=0.008,
            total_agents=100,
        ),
        emotion_config={
            "initial_fear": 0.15,
            "initial_greed": 0.55,
            "fear_inertia": 0.92,
            "greed_inertia": 0.92,
        }
    )

    market = controller.setup_market()
    emotion = controller.setup_emotion()
    belief_updater = BeliefUpdaterV2()

    # --- ?? KOL ?? ---
    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )

    # --- ???? + ???? ---
    narrative_engine = NarrativeEngine()
    propagator = PropagationModel(kol_network)

    # --- ????? ---
    monitor = ReflexivityMonitor()

    # --- ?? Agent ????? FundGenesis ??---
    from agents.emotional_retail import EmotionalRetailAgent
    from agents.trend_follower import TrendFollowerAgent
    from agents.value_investor import ValueInvestorAgent

    agents = []
    agent_types = []
    for i in range(100):
        if i < 10:
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
            agent_types.append("value")
        elif i < 40:
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
            agent_types.append("trend")
        else:
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))
            agent_types.append("retail")

    # --- ???? ---
    price_history = []
    emotion_history = []
    metrics_history = []
    narrative_history = []

    # --- ?100????? ---
    NARRATIVE_INJECTION_STEP = 30

    for step in range(steps):
        # ????
        if step == NARRATIVE_INJECTION_STEP:
            narrative = NarrativeEvent(
                name="AI??????",
                category=NarrativeCategory.FINTECH,
                polarity=Polarity.POSITIVE,
                target_sector="healthcare_ai",
                intensity=0.75,
                credibility=0.7,
                novelty=0.85,
                duration=80,
                source="MacroKOL",
            )
            narrative_engine.inject(narrative)
            propagator.inject_narrative(narrative)
            logger.info(f"Step {step}: Narrative injected - {narrative.name} (polarity={narrative.polarity.value}, intensity={narrative.intensity})")
            print(f"\n[Step {step}] [NARR] Narrative injected: {narrative.name}")
            print(f"    polarity={narrative.polarity.value}, intensity={narrative.intensity}")

        # --- ???? ---
        # 1. ????
        propagator.step()
        narrative_engine.tick()

        # 2. ?? ? ???BeliefUpdaterV2?
        belief_updater.update_all(
            agents=agents,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=narrative_engine,
        )

        # 3. ?? ? ???EmotionField?
        price_change = market.price_change_pct if market.price_history else 0.0
        narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)

        # 4. Agent ??
        market_snapshot = market.get_snapshot()
        for agent in agents:
            action = agent.decide(market.get_snapshot(), emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)

        # 5. ????
        market.update_price(emotion)

        # 6. ??????
        emotion.decay_toward_neutral(inertia=0.92)

        # 7. ??
        metrics = monitor.observe(
            step=step,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=narrative_engine,
            agents=agents,
        )
        metrics_history.append(metrics.as_dict())

        # ????
        price_history.append(market.price)
        emotion_history.append({
            "fear": emotion.fear,
            "greed": emotion.greed,
            "fg_index": emotion.fear_greed_index,
            "uncertainty": emotion.uncertainty,
        })

        if step % 30 == 0:
            logger.debug(f"Step {step}: Price={market.price:.2f}, Greed={emotion.greed:.3f}, Fear={emotion.fear:.3f}, RefIdx={metrics.reflexivity_index:.3f}, Bubble={metrics.bubble_risk_score:.3f}")
            print(f"  Step {step:3d} | Price: {market.price:7.2f} | "
                  f"Greed: {emotion.greed:.3f} | Fear: {emotion.fear:.3f} | "
                  f"RefIdx: {metrics.reflexivity_index:.3f} | "
                  f"Bubble: {metrics.bubble_risk_score:.3f}")

    # --- ????? ---
    _plot_positive_narrative_results(
        price_history, emotion_history, metrics_history, NARRATIVE_INJECTION_STEP,
        output_dir
    )

    # --- ???? ---
    final_metrics = metrics_history[-1]
    bubble_peaks = [m for m in metrics_history if m["regime"] == "bubble_peak"]
    critical_steps = monitor.critical_steps(threshold=0.5)

    result = {
        "demo": "positive_narrative_bubble",
        "description": "AI??????????",
        "final_price": round(price_history[-1], 2),
        "price_change_pct": round((price_history[-1] - price_history[0]) / price_history[0], 4),
        "final_reflexivity_index": final_metrics["reflexivity_index"],
        "final_bubble_risk": final_metrics["bubble_risk_score"],
        "peak_bubble_risk": round(max(m["bubble_risk_score"] for m in metrics_history), 4),
        "bubble_peak_count": len(bubble_peaks),
        "critical_alerts": len(critical_steps),
        "regime_distribution": monitor.regime_summary(),
    }

    # ????
    result_path = os.path.join(output_dir, "demo_positive_narrative_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Demo 1 completed: final_price={result['final_price']}, bubble_risk={result['final_bubble_risk']}")
    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"\n? Results saved to: {output_dir}/")

    return result


def _plot_positive_narrative_results(price_history, emotion_history, metrics_history,
                                      injection_step, output_dir):
    """??Demo????"""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    steps = range(len(price_history))

    # ?1???
    ax = axes[0]
    ax.plot(steps, price_history, 'b-', linewidth=1.5, label="Price")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7, label="Narrative Injection")
    ax.set_title("Demo 1: Price Path -- Positive Narrative Bubble", fontsize=12)
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(alpha=0.3)

    # ?2???
    ax = axes[1]
    fear = [e["fear"] for e in emotion_history]
    greed = [e["greed"] for e in emotion_history]
    ax.plot(steps, fear, 'r-', linewidth=1.5, label="Fear")
    ax.plot(steps, greed, 'g-', linewidth=1.5, label="Greed")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7)
    ax.set_title("Emotion Field Evolution")
    ax.set_ylabel("Index")
    ax.legend()
    ax.grid(alpha=0.3)

    # ?3?Reflexivity + Bubble Risk
    ax = axes[2]
    ref_idx = [m["reflexivity_index"] for m in metrics_history]
    bubble = [m["bubble_risk_score"] for m in metrics_history]
    ax.plot(steps, ref_idx, 'b-', linewidth=1.5, label="Reflexivity Index")
    ax.plot(steps, bubble, 'r-', linewidth=1.5, label="Bubble Risk Score")
    ax.axhline(y=0.6, color='orange', linestyle=':', alpha=0.7, label="Risk Threshold")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7)
    ax.set_title("Reflexivity Index & Bubble Risk")
    ax.set_xlabel("Step")
    ax.set_ylabel("Score")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "demo_positive_narrative.png")
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f" Chart saved: {fig_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    run_demo_positive_narrative(output_dir=args.output, steps=args.steps)
