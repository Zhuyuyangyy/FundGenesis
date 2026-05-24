"""
experiments/demo_falsification_collapse.py
==========================================
Demo 6: Narrative Falsification -> Trust Collapse

V0.3 Trust Bootstrapping — Demo 6

核心论点：
  正向叙事先引爆共识（形成泡沫），
  但当反向证据出现（价格开始下跌或官方辟谣）时，
  叙事被证伪 -> 信任崩塌 -> 叙事传播链断裂 -> 泡沫加速破裂

实验设计：
  1. Step 20：正常注入正向叙事（Macro KOL，高信任）
     -> 泡沫形成（价格上涨）
  2. Step 100：注入"反向证据"（官方辟谣 Narrative，negative polarity）
     -> 对同向叙事形成证伪信号
     -> credibility_penalty × 2.0（证伪惩罚）
     -> trust_level 崩塌（×0.1）
  3. Step 100-200：观察信任崩塌后的市场行为

成功标准：
  - Step 20-100：正向泡沫形成（价格↑，reflexivity↑）
  - Step 100+：trust_level 崩塌，泡沫破裂（价格急跌）
  - V0.3 能追踪 per-KOL trust 的崩塌过程
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

from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from trust.trust_decay_model import TrustDecayModel
from trust.credibility_updater import CredibilityUpdater


def run_demo_falsification_collapse(output_dir: str = None, steps: int = 300):
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "demo_v0.3_falsification"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Demo 6: Narrative Falsification -> Trust Collapse")
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

    # 高信任初始化（先形成泡沫）
    for kol in kol_network.get_kols():
        if kol.tier == KOLTier.MACRO:
            trust_engine.set_trust_level(kol.node_id, 0.95)
            trust_engine.set_credibility_score(kol.node_id, 0.90)
            trust_engine.set_price_validation(kol.node_id, 0.90)
        elif kol.tier == KOLTier.INFLUENCER:
            trust_engine.set_trust_level(kol.node_id, 0.80)

    trust_engine.update_follower_counts(kol_network)

    # ── Trust Decay Model ───────────────────────────────
    decay_model = TrustDecayModel()
    decay_model.attach_engine(trust_engine)

    # ── Propagation & Narrative ─────────────────────────
    base_propagator = PropagationModel(kol_network)
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
    trust_history = []        # per-step trust stats
    kol_trust_history = {}   # per-KOL trust history
    exposure_history = []

    NARR_INJECTION_STEP = 20       # 正向叙事注入
    FALSIFICATION_STEP = 100       # 证伪触发

    # 初始化 per-KOL 历史追踪
    for kol in kol_network.get_kols():
        kol_trust_history[kol.node_id] = []

    print(f"\n[Step 0] Starting simulation...")

    for step in range(steps):
        # ── Step 20: 正向叙事注入 ───────────────────
        if step == NARR_INJECTION_STEP:
            macro_kol = next((k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO), None)
            source_kol_id = macro_kol.node_id if macro_kol else None

            pos_narrative = NarrativeEvent(
                name="AI Medical Revolution",
                category=NarrativeCategory.FINTECH,
                polarity=Polarity.POSITIVE,
                target_sector="healthcare_ai",
                intensity=0.80,
                credibility=0.80,
                novelty=0.90,
                duration=80,
                source=source_kol_id,
            )
            narrative_engine.inject(pos_narrative)
            base_propagator.inject_narrative(pos_narrative)
            cred_updater.record_prediction(source_kol_id, pos_narrative, step)
            decay_model.record_narrative_injection(source_kol_id, step)

            source_trust = trust_engine.get_effective_trust(source_kol_id) if source_kol_id else 0.0
            print(f"\n[Step {step}] [NARR+] Positive narrative injected by {macro_kol.name if macro_kol else 'Unknown'}")
            print(f"    Source trust: {source_trust:.4f} -> BUBBLE FORMING")

        # ── Step 100: 证伪触发 ──────────────────────
        if step == FALSIFICATION_STEP:
            # 注入反向叙事（辟谣/证伪证据）
            neg_narrative = NarrativeEvent(
                name="AI Hype Debunked",
                category=NarrativeCategory.REGULATORY,
                polarity=Polarity.NEGATIVE,
                target_sector="healthcare_ai",
                intensity=0.90,
                credibility=0.85,
                novelty=0.95,
                duration=60,
                source="regulatory",
            )
            narrative_engine.inject(neg_narrative)
            base_propagator.inject_narrative(neg_narrative)

            # V0.3: 强制对之前的高信任 KOL 进行证伪更新
            for kol in kol_network.get_kols():
                if kol.tier in (KOLTier.MACRO, KOLTier.INFLUENCER):
                    state = trust_engine.get_state(kol.node_id)
                    if state:
                        old_trust = state.trust_level
                        old_cred = state.credibility_score
                        # 证伪惩罚（×0.1，崩塌）
                        trust_engine.set_trust_level(kol.node_id, old_trust * 0.1)
                        trust_engine.set_credibility_score(kol.node_id, old_cred * 0.1)
                        trust_engine.set_price_validation(kol.node_id, 0.0)
                        print(f"\n[Step {step}] [TRUST COLLAPSE] {kol.name}: "
                              f"trust {old_trust:.3f}->{old_trust*0.1:.3f}, "
                              f"cred {old_cred:.3f}->{old_cred*0.1:.3f}")

            print(f"\n[Step {step}] [NARR-] Falsification narrative injected -> TRUST COLLAPSE")

        # ── 传播 & 叙事 ───────────────────────────────
        base_propagator.step()
        narrative_engine.tick()

        # ── V0.3: Credibility Update（证伪检验）──────
        # 在证伪步之后，定期检查未验证叙事
        if step >= FALSIFICATION_STEP + 3:
            verified = cred_updater.verify_and_update(
                kol_network, price_history, step
            )
            for v in verified:
                if v.price_direction == "reject":
                    state = trust_engine.get_state(v.kol_id)
                    if state and state.trust_level > 0.01:
                        trust_engine.set_trust_level(v.kol_id, state.trust_level * 0.5)

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

        # ── V0.3: Trust Tracking ─────────────────────
        trust_stats = trust_engine.get_trust_statistics()
        trust_history.append({
            "step": step,
            "mean_trust": trust_stats.get("mean_trust", 0.0),
            "max_trust": trust_stats.get("max_trust", 0.0),
            "min_trust": trust_stats.get("min_trust", 0.0),
        })

        # Per-KOL trust
        for kol in kol_network.get_kols():
            state = trust_engine.get_state(kol.node_id)
            if state:
                kol_trust_history[kol.node_id].append({
                    "step": step,
                    "effective_trust": state.effective_trust,
                    "trust_level": state.trust_level,
                    "credibility_score": state.credibility_score,
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

        if step % 20 == 0 or step in (NARR_INJECTION_STEP, FALSIFICATION_STEP):
            t = trust_stats
            print(f"  Step {step:3d} | Price: {market.price:7.2f} | "
                  f"Greed: {emotion.greed:.3f} | Fear: {emotion.fear:.3f} | "
                  f"Trust(mean): {t.get('mean_trust', 0.0):.3f} | "
                  f"RefIdx: {metrics.reflexivity_index:.3f}")

    # ── Plotting ─────────────────────────────────────────
    _plot_falsification_results(
        price_history, emotion_history, metrics_history,
        trust_history, kol_trust_history, exposure_history,
        NARR_INJECTION_STEP, FALSIFICATION_STEP, output_dir
    )

    # ── Results ─────────────────────────────────────────
    final_metrics = metrics_history[-1]

    # 找价格峰值和证伪后的下跌
    pre_fals_price = price_history[FALSIFICATION_STEP] if FALSIFICATION_STEP < len(price_history) else price_history[-1]
    post_fals_peak = max(price_history[FALSIFICATION_STEP:]) if FALSIFICATION_STEP < len(price_history) else pre_fals_price
    post_fals_min = min(price_history[FALSIFICATION_STEP:]) if FALSIFICATION_STEP < len(price_history) else pre_fals_price

    result = {
        "demo": "falsification_trust_collapse",
        "v0.3_trust": True,
        "description": "High trust bubble -> falsification -> trust collapse -> crash",
        "initial_price": price_history[0],
        "pre_falsification_price": round(pre_fals_price, 2),
        "post_fals_peak": round(post_fals_peak, 2),
        "post_fals_min": round(post_fals_min, 2),
        "final_price": round(price_history[-1], 2),
        "collapse_occurred": post_fals_min < pre_fals_price * 0.85,  # 跌幅>15%认定崩塌
        "trust_at_falsification": round(trust_history[FALSIFICATION_STEP]["mean_trust"], 4) if FALSIFICATION_STEP < len(trust_history) else 0.0,
        "trust_at_end": round(trust_history[-1]["mean_trust"], 4),
        "final_reflexivity_index": final_metrics["reflexivity_index"],
        "peak_bubble_risk": round(max(m["bubble_risk_score"] for m in metrics_history), 4),
        "regime_distribution": monitor.regime_summary(),
        "verification_summary": cred_updater.get_verification_summary(),
    }

    result_path = os.path.join(output_dir, "demo_falsification_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    for k, v in result.items():
        if k not in ("regime_distribution", "verification_summary"):
            print(f"  {k}: {v}")
    print(f"\n  V0.3 Verification summary: {cred_updater.get_verification_summary()}")
    if result["collapse_occurred"]:
        print(f"\n  [OK] COLLAPSE CONFIRMED: Trust falsification triggered crash")
    else:
        print(f"\n  ⚠️ No significant collapse (check parameters)")

    print(f"\n  Results saved to: {output_dir}/")
    return result


def _plot_falsification_results(price_history, emotion_history, metrics_history,
                                 trust_history, kol_trust_history,
                                 exposure_history,
                                 injection_step, falsification_step,
                                 output_dir):
    fig, axes = plt.subplots(4, 1, figsize=(14, 13))

    steps = range(len(price_history))

    # Plot 1: Price (with falsification marker)
    ax = axes[0]
    ax.plot(steps, price_history, 'b-', linewidth=1.5, label="Price")
    ax.axvline(x=injection_step, color='green', linestyle='--', alpha=0.7,
               label=f"Narrative +{injection_step}")
    ax.axvline(x=falsification_step, color='red', linestyle='--', alpha=0.9,
               linewidth=2, label=f"Falsification {falsification_step}")
    ax.set_title("Demo 6: Falsification -> Trust Collapse\n"
                 "(Bubble formation -> Trust collapse -> Price crash)", fontsize=12)
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
    ax.axvline(x=falsification_step, color='red', linestyle='--', alpha=0.9, linewidth=2)
    ax.set_title("Emotion Field")
    ax.set_ylabel("Index")
    ax.legend()
    ax.grid(alpha=0.3)

    # Plot 3: V0.3 Trust Evolution (per-KOL)
    ax = axes[2]
    # 追踪 Macro KOL 的信任轨迹
    for kol_id, history in kol_trust_history.items():
        if history and len(history) > 0:
            first_state = history[0]
            # 只画前几个 step 看宏观趋势，抽样
            if len(history) > 5:
                eff_trusts = [h["effective_trust"] for h in history]
                steps_kol = [h["step"] for h in history]
                ax.plot(steps_kol, eff_trusts, alpha=0.4, linewidth=0.8)
    # 画平均值
    mean_trusts = [t["mean_trust"] for t in trust_history]
    steps_t = [t["step"] for t in trust_history]
    ax.plot(steps_t, mean_trusts, 'purple', linewidth=2.5, label="Mean Effective Trust")
    ax.axvline(x=falsification_step, color='red', linestyle='--', alpha=0.9, linewidth=2,
               label="Trust Collapse")
    ax.set_title("Demo 6: V0.3 Trust Collapse After Falsification")
    ax.set_ylabel("Effective Trust")
    ax.set_ylim(0.0, 1.0)
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
    ax.axvline(x=falsification_step, color='red', linestyle='--', alpha=0.9, linewidth=2)
    ax.set_title("Reflexivity & Bubble Risk")
    ax.set_xlabel("Step")
    ax.set_ylabel("Score")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, "demo_falsification.png")
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"  Chart saved: {fig_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    run_demo_falsification_collapse(output_dir=args.output, steps=args.steps)
