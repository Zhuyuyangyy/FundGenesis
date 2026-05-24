"""
Integrated Dashboard Runner for FundGenesis
Runs the WebSocket dashboard server and executes simulations
"""

import asyncio
import multiprocessing
import time
import sys
import os

def run_dashboard():
    """Run the WebSocket dashboard server in a separate process."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dashboard import app as dashboard_app
    import uvicorn
    print("[Dashboard] Starting WebSocket dashboard server on port 8765...")
    config = uvicorn.Config(dashboard_app.app, host="0.0.0.0", port=8765, log_level="warning")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())

def run_simulation(demo: int = 3):
    """Run a simulation with dashboard integration."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dashboard.ws_client import WsDashboardClient
    import threading

    ws_client = WsDashboardClient()
    client_thread = threading.Thread(target=ws_client.connect, daemon=True)
    client_thread.start()
    time.sleep(2)  # Wait for connection

    # Import the simulation
    from experiments.demo_narrative_reversal import run_demo_narrative_reversal
    from experiments.demo_positive_narrative import run_demo_positive_narrative
    from experiments.demo_regulatory_shock import run_demo_regulatory_shock

    demos = {
        1: (run_demo_positive_narrative, {"steps": 300}),
        2: (run_demo_regulatory_shock, {"steps": 300}),
        3: (run_demo_narrative_reversal, {"steps": 400}),
    }

    if demo not in demos:
        print(f"[Error] Demo {demo} not found")
        return

    run_fn, kwargs = demos[demo]
    print(f"[Simulation] Starting Demo {demo} with dashboard integration...")

    # Monkey-patch the experiment to send WebSocket updates
    original_plot = None

    def patched_run(output_dir=None, steps=400, _demo=demo, _run_fn=run_fn, _kwargs=kwargs):
        # Import needed modules
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

        agents = []
        for i in range(100):
            if i < 10:
                agents.append(ValueInvestorAgent(agent_id=f"VI_{i}"))
            elif i < 40:
                agents.append(TrendFollowerAgent(agent_id=f"TF_{i}"))
            else:
                agents.append(EmotionalRetailAgent(agent_id=f"ER_{i}"))

        # Event steps based on demo
        if _demo == 1:
            POSITIVE_STEP = 60
            REVERSAL_STEP = None
        elif _demo == 2:
            POSITIVE_STEP = None
            REVERSAL_STEP = 80
        else:
            POSITIVE_STEP = 60
            REVERSAL_STEP = 200

        for step in range(steps):
            # Narrative injection
            if POSITIVE_STEP and step == POSITIVE_STEP:
                narrative = NarrativeEvent(
                    name="AI医疗突破性进展" if _demo != 2 else "监管突然加强",
                    category=NarrativeCategory.FINTECH if _demo == 1 else NarrativeCategory.REGULATORY,
                    polarity=Polarity.POSITIVE if _demo == 1 else Polarity.NEGATIVE,
                    target_sector="healthcare_ai",
                    intensity=0.7,
                    credibility=0.65,
                    novelty=0.8,
                    duration=steps - POSITIVE_STEP - 1,
                    source="MacroKOL",
                )
                narrative_engine.inject(narrative)
                propagator.inject_narrative(narrative)
                ws_client.send({"narrative_event": {"name": narrative.name, "type": "positive"}, "step": step})

            if REVERSAL_STEP and step == REVERSAL_STEP:
                reversal_narrative = NarrativeEvent(
                    name="AI泡沫化质疑",
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
                ws_client.send({"narrative_event": {"name": reversal_narrative.name, "type": "reversal"}, "step": step})

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

            # Send to dashboard
            ws_client.send({
                "step": step,
                "price": market.price,
                "greed": emotion.greed,
                "fear": emotion.fear,
                "reflexivity_index": metrics.reflexivity_index,
                "bubble_risk": metrics.bubble_risk_score,
                "panic_risk": metrics.panic_risk_score,
                "regime": metrics.regime.value if hasattr(metrics.regime, 'value') else str(metrics.regime),
            })

            if step % 40 == 0:
                print(f"  Step {step:3d} | Price: {market.price:7.2f} | "
                      f"Greed: {emotion.greed:.3f} | Fear: {emotion.fear:.3f} | "
                      f"RefIdx: {metrics.reflexivity_index:.3f}")

        print(f"[Simulation] Demo {_demo} complete!")

    patched_run(output_dir=kwargs.get("output_dir"), steps=kwargs.get("steps", 400))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FundGenesis Dashboard + Simulation")
    parser.add_argument("--demo", type=int, choices=[1, 2, 3], default=3, help="Which demo to run")
    parser.add_argument("--dashboard-only", action="store_true", help="Run dashboard only")
    parser.add_argument("--sim-only", action="store_true", help="Run simulation only (no dashboard)")
    args = parser.parse_args()

    if args.dashboard_only:
        run_dashboard()
    elif args.sim_only:
        run_simulation(args.demo)
    else:
        # Run both: dashboard in background process, simulation in main
        import multiprocessing
        dp = multiprocessing.Process(target=run_dashboard, daemon=True)
        dp.start()
        print("[Main] Dashboard started in background process")
        time.sleep(2)
        try:
            run_simulation(args.demo)
        finally:
            dp.terminate()
