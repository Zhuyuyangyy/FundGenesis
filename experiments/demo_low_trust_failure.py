"""
experiments/demo_low_trust_failure.py
====================================
Demo 4: Low Trust KOL Propagation Failure

V0.3 Trust Bootstrapping — Demo 4

核心论点：
  当 KOL 信任分极低时（trust_level × credibility），即使叙事注入市场，
  也不会有效扩散 -> 信念不变 -> 行为不变 -> 价格不变。

实验设计：
  1. 初始化 KOL Network + Trust Engine（正常 bootstrap）
  2. 将所有 KOL trust_level × 0.2（低信任场景）
  3. Step 30 注入强正向叙事（intensity=0.85）
  4. 运行 300 步，追踪信任分、传播覆盖率、价格

成功标准（对比 V0.2 Baseline）：
  - Baseline: 正向叙事泡沫 100->276
  - Low Trust: 价格基本不变，泡沫不形成
  - 关键：trust_engine 追踪 per-KOL effective_trust
"""

import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.creator_controller import CreatorController, MarketConfig
from core.market_environment import MarketEnvironment
from core.emotion_field import EmotionField
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor

# V0.3 Trust imports
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from trust.trust_decay_model import TrustDecayModel
from trust.credibility_updater import CredibilityUpdater


def run_demo_low_trust_failure(output_dir: str = None, steps: int = 300):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.3_low_trust"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 4: Low Trust KOL Propagation Failure")
    print("=" * 60)

    # ── 市场环境 ─────────────────────────────────────────
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

    # ── KOL Network ─────────────────────────────────────
    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )

    # ── V0.3 Trust Engine ────────────────────────────────
    trust_config = TrustConfig()
    trust_engine = TrustEngine(trust_config)
    bootstrapper = TrustBootstrapper()
    bootstrapper.bootstrap_network(kol_network, trust_engine)

    # 关键操作：将所有 KOL 压到极低信任（×0.2）
    for kol in kol_network.get_kols():
        state = trust_engine.get_state(kol.node_id)
        if state:
            trust_engine.set_trust_level(kol.node_id, state.trust_level * 0.2)
            trust_engine.set_credibility_score(kol.node_id, 0.10)

    # 更新社会证明
    trust_engine.update_follower_counts(kol_network)

    print("\n[Trust Initialized - LOW MODE]")
    stats = trust_engine.get_trust_statistics()
    print(f"  Mean effective trust: {stats['mean_trust']:.4f}")
    print(f"  Max effective trust: {stats['max_trust']:.4f}")
    print(f"  Min effective trust: {stats['min_trust']:.4f}")

    # ── Propagation Model ────────────────────────────────
    base_propagator = PropagationModel(kol_network)

    # ── Narrative Engine ────────────────────────────────
    narrative_engine = NarrativeEngine()
    cred_updater = CredibilityUpdater()
    cred_updater.attach_engine(trust_engine)

    # ── Agents ─────────────────────────────────────────
    from agents.emotional_retail import EmotionalRetailAgent
    from agents.trend_follower import TrendFollowerAgent
    from agents.value_investor import ValueInvestorAgent

    agents = []
    for i in range(100):
        if i < 10:
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        elif i < 40:
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        else:
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

    # ── Monitor ────────────────────────────────────────
    monitor = ReflexivityMonitor()

    # ── Histories ──────────────────────────────────────
    price_history = []
    emotion_history = []
    metrics_history = []
    trust_history = []  # V0.3 新增
    exposure_history = []

    NARRATIVE_INJECTION_STEP = 30

    print(f"\n[Step 0] Starting simulation (trust LOW mode)...")

    for step in range(steps):
        # 叙事注入（Step 30）
        if step == NARRATIVE_INJECTION_STEP:
            # 找一个 macro KOL 作为叙事来源
            macro_kol = next((k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO), None)
            source_kol_id = macro_kol.node_id if macro_kol else None

            narrative = NarrativeEvent(
                name="AI Medical Revolution",
                category=NarrativeCategory.FINTECH,
                polarity=Polarity.POSITIVE,
                target_sector="healthcare_ai",
                intensity=0.85,   # 强叙事
                credibility=0.70,
                novelty=0.90,
                duration=80,
                source=source_kol_id,
            )
            narrative_engine.inject(narrative)
            base_propagator.inject_narrative(narrative)

            # V0.3：记录叙事来源
            source_eff_trust = trust_engine.get_effective_trust(source_kol_id) if source_kol_id else 0.0
            print(f"\n[Step {step}] [NARR] Narrative injected by {source_kol_id}")
            print(f"    Source KOL effective_trust: {source_eff_trust:.4f}")
            print(f"    (LOW TRUST: narrative expected to FAIL propagation)")

        # ── 传播 & 叙事 ───────────────────────────────
        base_propagator.step()
        narrative_engine.tick()

        # ── Belief Update ────────────────────────────
        belief_updater.update_all(
            agents=agents,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=narrative_engine,
        )

        # ── Emotion Update ────────────────────────────
        price_change = market.price_change_pct if market.price_history else 0.0
        narrative_engine.propagate_to_emotion(emotion, price_change_pct=price_change)

        # ── Agent Trading ────────────────────────────
        market_snapshot = market.get_snapshot()
        for agent in agents:
            action = agent.decide(market_snapshot, emotion)
            volume = agent.get_trade_volume()
            market.submit_order(agent.agent_id, action.value, volume)

        # ── Price Update ────────────────────────────────
        market.update_price(emotion)

        # ── Emotion Decay ────────────────────────────
        emotion.decay_toward_neutral(inertia=0.92)

        # ── V0.3: Trust Decay (每步) ─────────────────
        # （这里简化，不启用 decay，让低信任成为唯一变量）
        trust_stats = trust_engine.get_trust_statistics()
        trust_history.append({
            "step": step,
            "mean_trust": trust_stats.get("mean_trust", 0.0),
            "mean_effective": trust_stats.get("mean_trust", 0.0),
        })

        # ── Metrics ──────────────────────────────────
        metrics = monitor.observe(
            step=step,
            market=market,
            emotion=emotion,
            kol_network=kol_network,
            narrative_engine=narrative_engine,
            agents=agents,
        )
        metrics_history.append(metrics.as_dict())

        # ── Histories ────────────────────────────────
        price_history.append(market.price)
        exposure = kol_network.belief_statistics()
        exposure_history.append(exposure["mean_exposure"])
        emotion_history.append({"greed": emotion.greed, "fear": emotion.fear})

        if step % 30 == 0 or step == NARRATIVE_INJECTION_STEP:
            print(f"  Step {step:3d} | Price: {market.price:7.2f} | "
                  f"Greed: {emotion.greed:.3f} | Fear: {emotion.fear:.3f} | "
                  f"Exposure: {exposure['mean_exposure']:.3f} | "
                  f"Trust: {trust_stats.get('mean_trust', 0.0):.3f}")

    # ── Plotting ─────────────────────────────────────────
    _plot_low_trust_results(
        price_history, emotion_history, metrics_history,
        trust_history, exposure_history,
        NARRATIVE_INJECTION_STEP, output_dir
    )

    # ── Results ─────────────────────────────────────────
    final_metrics = metrics_history[-1]
    final_trust = trust_history[-1]

    # 计算泡沫是否形成（对比 V0.2 Baseline：价格从100->276）
    price_change_pct = (price_history[-1] - price_history[0]) / price_history[0]

    result = {
        "demo": "low_trust_propagation_failure",
        "v0.3_trust": True,
        "description": "Low trust KOL: narrative cannot propagate -> no bubble",
        "initial_price": price_history[0],
        "final_price": round(price_history[-1], 2),
        "price_change_pct": round(price_change_pct, 4),
        "v0.2_baseline_change": 1.76,   # 100->276 = +176%
        "propagation_suppressed": price_change_pct < 0.30,  # 涨幅<30%认为抑制成功
        "final_effective_trust": round(final_trust["mean_effective"], 4),
        "final_reflexivity_index": final_metrics["reflexivity_index"],
        "final_bubble_risk": final_metrics["bubble_risk_score"],
        "peak_bubble_risk": round(max(m["bubble_risk_score"] for m in metrics_history), 4),
        "trust_summary": trust_engine.get_trust_statistics(),
        "regime_distribution": monitor.regime_summary(),
    }

    result_path = os.path.join(output_dir, "demo_low_trust_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    for k, v in result.items():
        if k != "trust_summary":
            print(f"  {k}: {v}")
    print(f"\n  V0.2 Baseline: price 100 -> 276 (+176%)")
    print(f"  V0.3 Low Trust: price {price_history[0]:.0f} -> {price_history[-1]:.0f} ({price_change_pct*100:.1f}%)")
    if result["propagation_suppressed"]:
        print(f"\n  [OK] PROPAGATION SUPPRESSED: Low trust prevented bubble formation")
    else:
        print(f"\n  [WARNING] Bubble formed despite low trust (check parameters)")

    print(f"\n  Results saved to: {output_dir}/")
    return result


def _plot_low_trust_results(price_history, emotion_history, metrics_history,
                             trust_history, exposure_history,
                             injection_step, output_dir):
    fig, axes = plt.subplots(4, 1, figsize=(13, 12))

    steps = range(len(price_history))

    # Plot 1: Price
    ax = axes[0]
    ax.plot(steps, price_history, 'b-', linewidth=1.5, label="Price")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7, label="Narrative Injection")
    ax.set_title("Demo 4: Low Trust — Price Path\n(Expected: flat, no bubble)", fontsize=12)
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 2: Emotion
    ax = axes[1]
    fear = [e["fear"] for e in emotion_history]
    greed = [e["greed"] for e in emotion_history]
    ax.plot(steps, fear, 'r-', linewidth=1.5, label="Fear")
    ax.plot(steps, greed, 'g-', linewidth=1.5, label="Greed")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7)
    ax.set_title("Emotion Field")
    ax.set_ylabel("Index")
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 3: Trust (V0.3 NEW)
    ax = axes[2]
    mean_trusts = [t["mean_trust"] for t in trust_history]
    ax.plot(steps, mean_trusts, 'purple', linewidth=1.5, label="Mean Effective Trust")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7, label="Narrative Injection")
    ax.set_title("Demo 4: V0.3 Trust Evolution (LOW MODE)")
    ax.set_ylabel("Effective Trust")
    ax.set_ylim(0.0, 0.5)
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 4: Reflexivity + Bubble Risk
    ax = axes[3]
    ref_idx = [m["reflexivity_index"] for m in metrics_history]
    bubble = [m["bubble_risk_score"] for m in metrics_history]
    ax.plot(steps, ref_idx, 'b-', linewidth=1.5, label="Reflexivity Index")
    ax.plot(steps, bubble, 'r-', linewidth=1.5, label="Bubble Risk Score")
    ax.axhline(y=0.6, color='orange', linestyle=':', alpha=0.7, label="Risk Threshold")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7)
    ax.set_title("Reflexivity & Bubble Risk")
    ax.set_xlabel("Step")
    ax.set_ylabel("Score")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "demo_low_trust.png")
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"  Chart saved: {fig_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    run_demo_low_trust_failure(output_dir=args.output, steps=args.steps)
