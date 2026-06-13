"""
experiments/demo_narrative_reversal.py
=======================================
Demo 3???????????

???
  ?????? ? ?????? ? ???? ?
  ???????? ? ???? ?
  ???? ? ???? ? ????

???????????????????????????

?????
  - ???narrative_penetration? ? belief_concentration? ? reflexivity?
  - ??????????
  - ???panic_risk??capital_imbalance???????
"""

import os
import sys
import json
import logging
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger('FundGenesis.experiments.narrative_reversal')

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


def run_demo_narrative_reversal(output_dir: str = None, steps: int = 400):
    """??????Demo"""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs"
        )
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Starting Demo 3: Narrative Reversal - Bubble Burst")
    print("=" * 60)
    print("Demo 3: Narrative Reversal -- Bubble Burst")
    print("=" * 60)

    # --- ??? ---
    controller = CreatorController(
        market_config=MarketConfig(
            initial_price=100.0,
            impact_coefficient=0.20,
            noise_std=0.006,
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

    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )
    narrative_engine = NarrativeEngine()
    propagator = PropagationModel(kol_network)
    monitor = ReflexivityMonitor()

    # Agent ??
    agents = []
    for i in range(100):
        if i < 10:
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        elif i < 40:
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        else:
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

    price_history = []
    emotion_history = []
    metrics_history = []
    narrative_log = []

    POSITIVE_STEP = 60     # ??????
    REVERSAL_STEP = 200    # ??????

    for step in range(steps):
        # --- ?????? ---
        if step == POSITIVE_STEP:
            narrative = NarrativeEvent(
                name="AI???????????????",
                category=NarrativeCategory.FINTECH,
                polarity=Polarity.POSITIVE,
                target_sector="healthcare_ai",
                intensity=0.7,
                credibility=0.65,
                novelty=0.8,
                duration=steps - POSITIVE_STEP - 1,  # ???????
                source="MacroKOL",
            )
            narrative_engine.inject(narrative)
            propagator.inject_narrative(narrative)
            logger.info(f"Step {step}: Positive narrative injected - {narrative.name}")
            print(f"\n[Step {step}] [NARR] Positive narrative injected: {narrative.name}")
            narrative_log.append({"step": step, "event": "positive", "name": narrative.name})

        # --- ????????????---
        if step == REVERSAL_STEP:
            reversal_narrative = NarrativeEvent(
                name="AI????????????????",
                category=NarrativeCategory.MANIPULATION,
                polarity=Polarity.NEGATIVE,
                target_sector="healthcare_ai",
                intensity=0.85,
                credibility=0.8,
                novelty=0.95,
                duration=100,
                source="MacroKOL",
            )
            narrative_engine.inject(reversal_narrative)
            propagator.inject_narrative(reversal_narrative)
            logger.warning(f"Step {step}: NARRATIVE REVERSAL - {reversal_narrative.name}")
            print(f"\n[Step {step}] [REVR] NARRATIVE REVERSAL: {reversal_narrative.name}")
            narrative_log.append({"step": step, "event": "reversal", "name": reversal_narrative.name})

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
        emotion.decay_toward_neutral(inertia=0.90)

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
            "confidence": emotion.confidence,
        })

        if step % 40 == 0:
            logger.debug(f"Step {step}: Price={market.price:.2f}, Greed={emotion.greed:.3f}, Fear={emotion.fear:.3f}, RefIdx={metrics.reflexivity_index:.3f}, Bubble={metrics.bubble_risk_score:.3f}, Panic={metrics.panic_risk_score:.3f}")
            print(f"  Step {step:3d} | Price: {market.price:7.2f} | "
                  f"Greed: {emotion.greed:.3f} | Fear: {emotion.fear:.3f} | "
                  f"RefIdx: {metrics.reflexivity_index:.3f} | "
                  f"Bubble: {metrics.bubble_risk_score:.3f} | "
                  f"Panic: {metrics.panic_risk_score:.3f}")

    # --- ??? ---
    _plot_reversal_results(
        price_history, emotion_history, metrics_history,
        POSITIVE_STEP, REVERSAL_STEP, output_dir
    )

    final_metrics = metrics_history[-1]
    peak_bubble = max(m["bubble_risk_score"] for m in metrics_history)
    peak_panic = max(m["panic_risk_score"] for m in metrics_history)

    result = {
        "demo": "narrative_reversal_bubble_burst",
        "description": "??????????",
        "initial_price": round(price_history[0], 2),
        "peak_price": round(max(price_history), 2),
        "peak_price_step": price_history.index(max(price_history)),
        "final_price": round(price_history[-1], 2),
        "peak_bubble_risk": round(peak_bubble, 4),
        "peak_panic_risk": round(peak_panic, 4),
        "final_reflexivity_index": final_metrics["reflexivity_index"],
        "regime_distribution": monitor.regime_summary(),
        "narrative_log": narrative_log,
    }

    result_path = os.path.join(output_dir, "demo_narrative_reversal_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Demo 3 completed: final_price={result['final_price']}, peak_price={result['peak_price']}, peak_bubble={result['peak_bubble_risk']}")
    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"\n? Results saved to: {output_dir}/")

    return result


def _plot_reversal_results(price_history, emotion_history, metrics_history,
                            positive_step, reversal_step, output_dir):
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    steps = range(len(price_history))

    # ?1??? + ??????
    ax = axes[0]
    ax.plot(steps, price_history, 'b-', linewidth=1.5, label="Price")
    peak_idx = price_history.index(max(price_history))
    ax.axvline(x=positive_step, color='green', linestyle='--', alpha=0.7, label="+ Narrative")
    ax.axvline(x=reversal_step, color='red', linestyle='--', alpha=0.8, label="Reversal")
    ax.axvline(x=peak_idx, color='orange', linestyle=':', alpha=0.8, label=f"Peak ({peak_idx})")
    ax.scatter([peak_idx], [max(price_history)], color='orange', s=80, zorder=5)
    ax.set_title("Demo 3: Price Path -- Bubble Formation & Burst", fontsize=12)
    ax.set_ylabel("Price")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ?2??????
    ax = axes[1]
    greed = [e["greed"] for e in emotion_history]
    fear = [e["fear"] for e in emotion_history]
    ax.plot(steps, greed, 'g-', linewidth=1.5, label="Greed")
    ax.plot(steps, fear, 'r-', linewidth=1.5, label="Fear")
    ax.plot(steps, [g - f for g, f in zip(greed, fear)], 'b--', linewidth=1, alpha=0.5, label="Greed-Fear")
    ax.axvline(x=positive_step, color='green', linestyle='--', alpha=0.7)
    ax.axvline(x=reversal_step, color='red', linestyle='--', alpha=0.8)
    ax.set_title("Emotion Field -- Greed vs Fear")
    ax.set_ylabel("Index")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ?3????? + ????
    ax = axes[2]
    bubble = [m["bubble_risk_score"] for m in metrics_history]
    panic = [m["panic_risk_score"] for m in metrics_history]
    ref_idx = [m["reflexivity_index"] for m in metrics_history]
    ax.fill_between(steps, bubble, alpha=0.3, color='orange', label="Bubble Risk")
    ax.fill_between(steps, panic, alpha=0.3, color='red', label="Panic Risk")
    ax.plot(steps, ref_idx, 'b-', linewidth=1.2, label="Reflexivity Index")
    ax.axhline(y=0.6, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=positive_step, color='green', linestyle='--', alpha=0.7)
    ax.axvline(x=reversal_step, color='red', linestyle='--', alpha=0.8)
    ax.set_title("Bubble Risk vs Panic Risk -- Reflexivity Index")
    ax.set_xlabel("Step")
    ax.set_ylabel("Score")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "demo_narrative_reversal.png")
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f" Chart saved: {fig_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    run_demo_narrative_reversal(output_dir=args.output, steps=args.steps)
