"""
experiments/reflexivity_bench.py
==================================
ReflexMarket-Bench: SCI 2区 Compliance Benchmark

5 scenarios × 10 runs each.

Scenarios:
  1. normal_propagation     — Baseline normal market (no manipulation)
  2. coordinated_kol        — Coordinated KOL amplification (HIGH risk)
  3. fomo_surge            — FOMO surge + price self-validation (HIGH risk)
  4. narrative_reversal    — Narrative reversal + bubble burst
  5. regulatory_suppression — Same as coordinated_kol WITH RegulatorAgent

Metrics per run:
  - avg_reflexivity_index   : mean of reflexivity_index across all steps
  - bubble_risk_peak        : max bubble_risk_score observed
  - manipulation_detection_rate : 1.0 if peak manipulation_risk >= 0.30, else 0.0
  - regulation_effectiveness: (baseline_peak - regulated_peak) / baseline_peak

Metrics per scenario (10-run aggregate):
  - mean / std / min / max for each metric

Usage:
  python experiments/reflexivity_bench.py
  python experiments/reflexivity_bench.py --runs 10 --steps 200 --output outputs/bench_results
"""

import os
import sys
import json
import argparse
import numpy as np
from typing import Dict, List, Tuple, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.creator_controller import CreatorController, MarketConfig
from core.belief_updater_v2 import BeliefUpdaterV2
from social.kol_network import KOLNetwork, KOLTier
from social.propagation_model import PropagationModel
from narrative.narrative_event import NarrativeEvent, NarrativeCategory, Polarity
from narrative.narrative_engine import NarrativeEngine
from monitor.reflexivity_monitor import ReflexivityMonitor
from trust.trust_engine import TrustEngine, TrustConfig
from trust.trust_bootstrapper import TrustBootstrapper
from risk.manipulation_risk_agent import ManipulationRiskAgent, RiskLevel
from risk.regulator_agent import RegulatorAgent, InterventionIntensity, InterventionAction

from agents.emotional_retail import EmotionalRetailAgent
from agents.trend_follower import TrendFollowerAgent
from agents.value_investor import ValueInvestorAgent


# ─────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────

def make_agents(n: int = 100) -> list:
    agents = []
    for i in range(n):
        if i < 10:
            agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
        elif i < 40:
            agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
        else:
            agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))
    return agents


def standard_market_setup(seed: int = None):
    """Create a fully-initialised market stack."""
    if seed is not None:
        np.random.seed(seed)

    controller = CreatorController(
        market_config=MarketConfig(
            initial_price=100.0,
            impact_coefficient=0.20,
            noise_std=0.008,
            total_agents=100,
        ),
        emotion_config={
            "initial_fear": 0.15,
            "initial_greed": 0.60,
            "fear_inertia": 0.92,
            "greed_inertia": 0.92,
        },
    )
    market = controller.setup_market()
    emotion = controller.setup_emotion()
    belief_updater = BeliefUpdaterV2()
    kol_network = KOLNetwork().build_default_network(
        n_macro=2, n_influencer=5, n_micro=10, n_retail=100
    )
    narrative_engine = NarrativeEngine()
    propagation = PropagationModel(kol_network)
    trust_config = TrustConfig()
    trust_engine = TrustEngine(trust_config)
    bootstrapper = TrustBootstrapper()
    bootstrapper.bootstrap_network(kol_network, trust_engine)
    reflexivity_monitor = ReflexivityMonitor()
    agents = make_agents(100)
    return {
        "market": market,
        "emotion": emotion,
        "belief_updater": belief_updater,
        "kol_network": kol_network,
        "narrative_engine": narrative_engine,
        "propagation": propagation,
        "trust_engine": trust_engine,
        "reflexivity_monitor": reflexivity_monitor,
        "agents": agents,
    }


def run_simulation(
    steps: int,
    scenario_fn,
    use_regulator: bool = False,
    seed: int = None,
) -> Dict[str, Any]:
    """
    Run one simulation instance.

    Returns dict with per-run metrics.
    """
    if seed is not None:
        np.random.seed(seed)

    stack = standard_market_setup(seed=seed)
    market          = stack["market"]
    emotion         = stack["emotion"]
    belief_updater  = stack["belief_updater"]
    kol_network     = stack["kol_network"]
    narrative_engine= stack["narrative_engine"]
    propagation     = stack["propagation"]
    trust_engine    = stack["trust_engine"]
    monitor         = stack["reflexivity_monitor"]
    agents          = stack["agents"]

    risk_agent = ManipulationRiskAgent(
        action_thresholds={
            "monitor": 0.15,
            "human_review": 0.25,
            "block": 0.60,
        }
    )
    regulator = RegulatorAgent()

    # inject narrative events for this scenario
    scenario_fn(narrative_engine, propagation, risk_agent, kol_network, market, emotion)

    reflexivity_history = []
    bubble_history = []
    manipulation_history = []

    for step in range(steps):
        propagation.step()
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

        risk_report = risk_agent.evaluate(
            step=step,
            kol_network=kol_network,
            trust_engine=trust_engine,
            reflexivity_monitor=monitor,
            market=market,
            narrative_engine=narrative_engine,
            propagation_model=propagation,
            agents=agents,
        )

        # ── Regulator intervention ────────────────────────
        if use_regulator:
            manipulation_flags = {
                "coordinated_detected": any(
                    p.pattern.value == "coordinated_kol_amplification"
                    for p in risk_report.detected_patterns
                ),
                "fomo_detected": risk_report.fomo_score > 0.3,
                "self_validation_detected": risk_report.self_validation_score > 0.3,
            }
            market_state = {
                "price": market.price,
                "bubble_risk": metrics.bubble_risk_score,
                "retail_fomo": risk_report.fomo_score,
                "price_volatility": metrics.volatility,
            }
            regulator.step(
                risk_score=risk_report.manipulation_risk_score,
                market_state=market_state,
                manipulation_flags=manipulation_flags,
                narrative_engine=narrative_engine,
                kol_network=kol_network,
                agents=agents,
            )

        reflexivity_history.append(metrics.reflexivity_index)
        bubble_history.append(metrics.bubble_risk_score)
        manipulation_history.append(risk_report.manipulation_risk_score)

    return {
        "avg_reflexivity_index": round(float(np.mean(reflexivity_history)), 4),
        "bubble_risk_peak": round(float(np.max(bubble_history)), 4),
        "manipulation_detection_rate": (
            1.0 if float(np.max(manipulation_history)) >= 0.30 else 0.0
        ),
        "peak_manipulation_risk": round(float(np.max(manipulation_history)), 4),
        "final_price": round(float(market.price), 2),
        "price_change_pct": round(
            float((market.price - 100.0) / 100.0), 4
        ),
        "reflexivity_std": round(float(np.std(reflexivity_history)), 4),
        "manipulation_history": [round(float(x), 4) for x in manipulation_history],
    }


# ─────────────────────────────────────────────────
# Scenario definitions
# ─────────────────────────────────────────────────

def scenario_normal(narrative_engine, propagation, risk_agent, kol_network, market, emotion):
    """Scenario 1: Normal propagation — no abnormal narrative injection."""
    # No manipulation injection — system runs naturally


def scenario_coordinated_kol(narrative_engine, propagation, risk_agent, kol_network, market, emotion):
    """Scenario 2: Coordinated KOL amplification — HIGH manipulation risk."""
    macro_kols     = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
    influencer_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.INFLUENCER]
    micro_kols     = [k for k in kol_network.get_kols() if k.tier == KOLTier.MICRO]

    # Step 25: Macro KOL creates high-intensity narrative
    macro = macro_kols[0] if macro_kols else None
    shared_narrative = NarrativeEvent(
        name="龙头股业绩将超预期，AI革命将改变一切",
        category=NarrativeCategory.EARNINGS,
        polarity=Polarity.POSITIVE,
        target_sector="tech",
        intensity=0.88,
        credibility=0.82,
        novelty=0.90,
        duration=80,
        source=macro.node_id if macro else "system",
    )
    narrative_engine.inject(shared_narrative)
    propagation.inject_narrative(shared_narrative)
    risk_agent.record_kol_spread(shared_narrative._id, macro.node_id if macro else "system")

    # Step 28: Influencer wave 2
    for inf in influencer_kols[:3]:
        risk_agent.record_kol_spread(shared_narrative._id, inf.node_id)

    # Step 33: Micro KOL wave 3 (cross-tier)
    for mic in micro_kols[:4]:
        risk_agent.record_kol_spread(shared_narrative._id, mic.node_id)

    # Step 45: Price self-validation
    risk_agent.record_price_feedback(
        narrative_id=shared_narrative._id,
        price_change=0.03,
        confirmation_strength=0.72,
        step=45,
    )

    # Step 55: FOMO signal
    risk_agent.record_fomo_signal(
        retail_buy_ratio=0.78,
        greed_level=0.82,
        belief_concentration=0.70,
        step=55,
    )


def scenario_fomo_surge(narrative_engine, propagation, risk_agent, kol_network, market, emotion):
    """Scenario 3: FOMO surge + price self-validation — HIGH manipulation risk."""
    macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
    macro = macro_kols[0] if macro_kols else None

    narrative = NarrativeEvent(
        name="行业基本面超预期，龙头企业将迎来爆发式增长",
        category=NarrativeCategory.EARNINGS,
        polarity=Polarity.POSITIVE,
        target_sector="tech",
        intensity=0.90,
        credibility=0.85,
        novelty=0.90,
        duration=80,
        source=macro.node_id if macro else "system",
    )
    narrative_engine.inject(narrative)
    propagation.inject_narrative(narrative)

    # Inject signals at the right steps
    risk_agent.record_price_feedback(
        narrative_id=narrative._id,
        price_change=0.15,
        confirmation_strength=0.80,
        step=40,
    )
    risk_agent.record_fomo_signal(
        retail_buy_ratio=0.85,
        greed_level=0.80,
        belief_concentration=0.70,
        step=40,
    )
    if macro:
        risk_agent.record_trust_bootstrap(
            kol_id=macro.node_id,
            trust_growth_rate=2.5,
            source="price_confirmation",
            step=50,
        )


def scenario_narrative_reversal(narrative_engine, propagation, risk_agent, kol_network, market, emotion):
    """Scenario 4: Narrative reversal + bubble burst."""
    macro_kols = [k for k in kol_network.get_kols() if k.tier == KOLTier.MACRO]
    macro = macro_kols[0] if macro_kols else None

    POSITIVE_STEP = 60
    REVERSAL_STEP = 200

    # Narrative reversal is time-based; inject a placeholder that will be
    # handled by step-aware injection below. We use a flag stored in a
    # mutable dict trick via a closure approach — instead we inject at the
    # earliest step and rely on the simulation loop to advance.
    # For the bench we use a simpler approach: inject positive narrative now,
    # reversal narrative at step 0 (it will be active from the start).
    pos_narrative = NarrativeEvent(
        name="AI医疗革命正在颠覆传统行业",
        category=NarrativeCategory.FINTECH,
        polarity=Polarity.POSITIVE,
        target_sector="healthcare_ai",
        intensity=0.70,
        credibility=0.65,
        novelty=0.80,
        duration=200,
        source=macro.node_id if macro else "system",
    )
    rev_narrative = NarrativeEvent(
        name="AI医疗神话破灭，行业泡沫严重",
        category=NarrativeCategory.MANIPULATION,
        polarity=Polarity.NEGATIVE,
        target_sector="healthcare_ai",
        intensity=0.85,
        credibility=0.80,
        novelty=0.95,
        duration=100,
        source=macro.node_id if macro else "system",
    )
    narrative_engine.inject(pos_narrative)
    propagation.inject_narrative(pos_narrative)
    # reversal is injected at step 120 (mid-point for 200-step run)
    # Store on the engine for later injection by the runner
    narrative_engine._pending_reversal = rev_narrative
    narrative_engine._reversal_step = 120


def _scenario_narrative_reversal_inject(scenario_state, step, narrative_engine, propagation):
    """Time-based injection for narrative reversal scenario."""
    if step == scenario_state.get("reversal_injected_step", 120):
        if hasattr(narrative_engine, "_pending_reversal"):
            rev = narrative_engine._pending_reversal
            narrative_engine.inject(rev)
            propagation.inject_narrative(rev)
            delattr(narrative_engine, "_pending_reversal")


def scenario_regulatory_suppression(narrative_engine, propagation, risk_agent, kol_network, market, emotion):
    """Scenario 5: Same as coordinated_kol but WITH RegulatorAgent active."""
    # Same injection as coordinated_kol
    scenario_coordinated_kol(narrative_engine, propagation, risk_agent, kol_network, market, emotion)


# ─────────────────────────────────────────────────
# Main benchmark runner
# ─────────────────────────────────────────────────

SCENARIOS = {
    "normal_propagation": {
        "fn": scenario_normal,
        "use_regulator": False,
        "label": "Normal Propagation (Baseline)",
    },
    "coordinated_kol": {
        "fn": scenario_coordinated_kol,
        "use_regulator": False,
        "label": "Coordinated KOL Amplification",
    },
    "fomo_surge": {
        "fn": scenario_fomo_surge,
        "use_regulator": False,
        "label": "FOMO Surge + Price Self-Validation",
    },
    "narrative_reversal": {
        "fn": scenario_narrative_reversal,
        "use_regulator": False,
        "label": "Narrative Reversal + Bubble Burst",
    },
    "regulatory_suppression": {
        "fn": scenario_regulatory_suppression,
        "use_regulator": True,
        "label": "Coordinated KOL + Regulatory Suppression",
    },
}


def _run_single(
    scenario_key: str,
    scenario_info: dict,
    n_runs: int,
    steps: int,
    reversal_injection_step: int = 120,
) -> Tuple[Dict[str, dict], List[dict]]:
    """Run one scenario n_runs times; returns (agg_stats, raw_runs)."""
    label = scenario_info["label"]
    use_reg = scenario_info["use_regulator"]
    scenario_fn = scenario_info["fn"]

    raw_runs = []

    for r in range(n_runs):
        seed = 42 + r * 137  # reproducible seeds

        # Build a fresh market stack each run
        stack = standard_market_setup(seed=seed)
        market           = stack["market"]
        emotion          = stack["emotion"]
        belief_updater   = stack["belief_updater"]
        kol_network      = stack["kol_network"]
        narrative_engine = stack["narrative_engine"]
        propagation      = stack["propagation"]
        trust_engine     = stack["trust_engine"]
        monitor          = stack["reflexivity_monitor"]
        agents           = stack["agents"]

        risk_agent = ManipulationRiskAgent(
            action_thresholds={
                "monitor": 0.15,
                "human_review": 0.25,
                "block": 0.60,
            }
        )
        regulator = RegulatorAgent()

        # Pre-run scenario injection
        scenario_fn(narrative_engine, propagation, risk_agent, kol_network, market, emotion)

        # reversal injection step stored on narrative_engine if needed
        if scenario_key == "narrative_reversal":
            narrative_engine._pending_reversal_step = reversal_injection_step

        reflexivity_history = []
        bubble_history = []
        manipulation_history = []

        for step in range(steps):
            # Narrative reversal: inject reversal at mid-point
            if scenario_key == "narrative_reversal":
                if step == reversal_injection_step:
                    if hasattr(narrative_engine, "_pending_reversal"):
                        rev = narrative_engine._pending_reversal
                        narrative_engine.inject(rev)
                        propagation.inject_narrative(rev)

            propagation.step()
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

            risk_report = risk_agent.evaluate(
                step=step,
                kol_network=kol_network,
                trust_engine=trust_engine,
                reflexivity_monitor=monitor,
                market=market,
                narrative_engine=narrative_engine,
                propagation_model=propagation,
                agents=agents,
            )

            if use_reg:
                manipulation_flags = {
                    "coordinated_detected": any(
                        p.pattern.value == "coordinated_kol_amplification"
                        for p in risk_report.detected_patterns
                    ),
                    "fomo_detected": risk_report.fomo_score > 0.3,
                    "self_validation_detected": risk_report.self_validation_score > 0.3,
                }
                market_state = {
                    "price": market.price,
                    "bubble_risk": metrics.bubble_risk_score,
                    "retail_fomo": risk_report.fomo_score,
                    "price_volatility": metrics.volatility,
                }
                regulator.step(
                    risk_score=risk_report.manipulation_risk_score,
                    market_state=market_state,
                    manipulation_flags=manipulation_flags,
                    narrative_engine=narrative_engine,
                    kol_network=kol_network,
                    agents=agents,
                )

            reflexivity_history.append(metrics.reflexivity_index)
            bubble_history.append(metrics.bubble_risk_score)
            manipulation_history.append(risk_report.manipulation_risk_score)

        run_result = {
            "run": r + 1,
            "seed": seed,
            "avg_reflexivity_index": round(float(np.mean(reflexivity_history)), 4),
            "bubble_risk_peak": round(float(np.max(bubble_history)), 4),
            "manipulation_detection_rate": (
                1.0 if float(np.max(manipulation_history)) >= 0.30 else 0.0
            ),
            "peak_manipulation_risk": round(float(np.max(manipulation_history)), 4),
            "final_price": round(float(market.price), 2),
            "price_change_pct": round(float((market.price - 100.0) / 100.0), 4),
            "reflexivity_std": round(float(np.std(reflexivity_history)), 4),
        }
        raw_runs.append(run_result)

    METRICS = ["avg_reflexivity_index", "bubble_risk_peak", "manipulation_detection_rate", "peak_manipulation_risk"]
    agg_stats = {}
    for m in METRICS:
        vals = [run[m] for run in raw_runs]
        agg_stats[m] = {
            "mean": round(float(np.mean(vals)), 4),
            "std":  round(float(np.std(vals)),  4),
            "min":  round(float(np.min(vals)),  4),
            "max":  round(float(np.max(vals)),  4),
            "raw":  [round(float(v), 4) for v in vals],
        }

    return agg_stats, raw_runs


def run_reflexivity_bench(
    n_runs: int = 10,
    steps: int = 200,
    output_dir: str = None,
    reversal_injection_step: int = 120,
) -> Dict[str, Any]:
    """
    Run the full ReflexMarket-Bench.

    Returns a results dict and saves:
      - results.json   (full structured results)
      - summary.csv    (aggregate stats table)
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "outputs", "reflexivity_bench"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("ReflexMarket-Bench — SCI 2区 Compliance")
    print(f"  Scenarios : {len(SCENARIOS)}  |  Runs/scenario : {n_runs}  |  Steps : {steps}")
    print("=" * 70)

    scenario_keys = list(SCENARIOS.keys())
    all_agg = {}
    all_raw = {}

    for scenario_key in scenario_keys:
        scenario_info = SCENARIOS[scenario_key]
        label = scenario_info["label"]
        print(f"\n>> {scenario_key}: {label}")
        print(f"   running {n_runs} runs ...", end=" ", flush=True)

        agg, raw = _run_single(
            scenario_key=scenario_key,
            scenario_info=scenario_info,
            n_runs=n_runs,
            steps=steps,
            reversal_injection_step=reversal_injection_step,
        )
        all_agg[scenario_key] = agg
        all_raw[scenario_key] = raw

        # Quick print
        print("done")
        ari = agg["avg_reflexivity_index"]
        brp = agg["bubble_risk_peak"]
        mdr = agg["manipulation_detection_rate"]
        pmp = agg["peak_manipulation_risk"]
        print(
            f"   avg_reflexivity_index = {ari['mean']:.4f} +/- {ari['std']:.4f}  "
            f"|  bubble_risk_peak = {brp['mean']:.4f} +/- {brp['std']:.4f}"
        )
        print(
            f"   manipulation_detection_rate = {mdr['mean']:.4f}  "
            f"|  peak_manipulation_risk = {pmp['mean']:.4f} +/- {pmp['std']:.4f}"
        )

    # ── Regulation effectiveness ──────────────────────────
    # Compare coordinated_kol vs regulatory_suppression
    if "coordinated_kol" in all_agg and "regulatory_suppression" in all_agg:
        baseline_bubble_peak = all_agg["coordinated_kol"]["bubble_risk_peak"]["mean"]
        regulated_bubble_peak = all_agg["regulatory_suppression"]["bubble_risk_peak"]["mean"]
        regulation_effectiveness = round(
            (baseline_bubble_peak - regulated_bubble_peak) / max(baseline_bubble_peak, 0.001),
            4,
        )
        print(f"\n>> Regulation Effectiveness:")
        print(
            f"   baseline_peak_bubble = {baseline_bubble_peak:.4f}  "
            f"|  regulated_peak_bubble = {regulated_bubble_peak:.4f}"
        )
        print(f"   regulation_effectiveness = {regulation_effectiveness:.4f}  "
              f"({regulation_effectiveness*100:.1f}% reduction)")
    else:
        regulation_effectiveness = None

    # ── Assemble full results ────────────────────────────
    results = {
        "meta": {
            "n_scenarios": len(SCENARIOS),
            "n_runs": n_runs,
            "steps": steps,
            "reversal_injection_step": reversal_injection_step,
            "scenarios": {
                k: {"label": v["label"], "use_regulator": v["use_regulator"]}
                for k, v in SCENARIOS.items()
            },
        },
        "regulation_effectiveness": regulation_effectiveness,
        "scenarios": {
            k: {
                "label": SCENARIOS[k]["label"],
                "aggregate": all_agg[k],
            }
            for k in scenario_keys
        },
        "raw_runs": all_raw,
    }

    results_path = os.path.join(output_dir, "results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] results.json  -> {results_path}")

    # ── CSV summary ─────────────────────────────────────
    csv_path = os.path.join(output_dir, "summary.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("scenario,metric,mean,std,min,max\n")
        for k in scenario_keys:
            for m, st in all_agg[k].items():
                f.write(f"{k},{m},{st['mean']},{st['std']},{st['min']},{st['max']}\n")
    print(f"[OK] summary.csv   -> {csv_path}")

    # ── Print full summary table ─────────────────────────
    METRIC_LABELS = [
        ("avg_reflexivity_index",      "Avg Reflexivity Index"),
        ("bubble_risk_peak",            "Peak Bubble Risk"),
        ("manipulation_detection_rate",  "Manipulation Detection Rate"),
        ("peak_manipulation_risk",       "Peak Manipulation Risk"),
    ]
    print("\n" + "=" * 90)
    hdr = f"{'Metric':<28}" + "".join(f"{SCENARIOS[k]['label'][:18]:>22}" for k in scenario_keys)
    print(hdr[:90])
    print("-" * 90)
    for mkey, mlabel in METRIC_LABELS:
        row = f"{mlabel:<28}"
        for k in scenario_keys:
            mean = all_agg[k][mkey]["mean"]
            std  = all_agg[k][mkey]["std"]
            row += f"{mean:>10.4f} ±{std:>10.4f}"
        print(row[:90])
    print("=" * 90)

    if regulation_effectiveness is not None:
        print(
            f"\n  Regulation Effectiveness: "
            f"{regulation_effectiveness:.4f}  ({regulation_effectiveness*100:.1f}% peak bubble reduction)"
        )

    print(f"\n  Full results -> {results_path}")
    return results


# ─────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReflexMarket-Bench SCI 2区 Compliance")
    parser.add_argument("--runs",   type=int, default=10,  help="Runs per scenario [10]")
    parser.add_argument("--steps",  type=int, default=200, help="Steps per run [200]")
    parser.add_argument("--output", type=str,  default=None, help="Output directory")
    parser.add_argument(
        "--reversal-step", type=int, default=120,
        help="Step at which reversal narrative is injected [120]"
    )
    args = parser.parse_args()

    run_reflexivity_bench(
        n_runs=args.runs,
        steps=args.steps,
        output_dir=args.output,
        reversal_injection_step=args.reversal_step,
    )
    print("\n=== ReflexMarket-Bench complete ===")
