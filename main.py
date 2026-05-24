"""
FundGenesis V0.2 ? ReflexMarket-AI
====================================
????

???
  python main.py                              # V0.1 ??????
  python main.py --herding                   # V0.1 ??????
  python main.py --blackswan                  # V0.1 ?????
  python main.py --v02                        # V0.2 ReflexMarket-AI ?? Demo
  python main.py --demo 1                     # Demo 1?????????
  python main.py --demo 2                     # Demo 2?????????
  python main.py --demo 3                     # Demo 3?????????
  python main.py --all                        # ??????
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    args = sys.argv[1:]
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    if "--all" in args:
        print("=" * 60)
        print("FundGenesis V0.2 ? ReflexMarket-AI")
        print("Running ALL Experiments (V0.1 + V0.2)")
        print("=" * 60)

        # V0.1 experiments
        from experiments.emotion_shock import run_emotion_shock_experiment
        run_emotion_shock_experiment(output_dir=output_dir)

        # V0.2 Demo 1
        print("\n" + "=" * 60)
        from experiments.demo_positive_narrative import run_demo_positive_narrative
        run_demo_positive_narrative(output_dir=output_dir, steps=300)

        # V0.2 Demo 2
        print("\n" + "=" * 60)
        from experiments.demo_regulatory_shock import run_demo_regulatory_shock
        run_demo_regulatory_shock(output_dir=output_dir, steps=300)

        # V0.2 Demo 3
        print("\n" + "=" * 60)
        from experiments.demo_narrative_reversal import run_demo_narrative_reversal
        run_demo_narrative_reversal(output_dir=output_dir, steps=400)

        print("\n[OK] All V0.2 experiments complete!")
        print(f"[DIR] Results saved to: {output_dir}/")

    elif "--v02" in args:
        print("=" * 60)
        print("FundGenesis V0.2 ? ReflexMarket-AI Demos")
        print("=" * 60)
        from experiments.demo_positive_narrative import run_demo_positive_narrative
        from experiments.demo_regulatory_shock import run_demo_regulatory_shock
        from experiments.demo_narrative_reversal import run_demo_narrative_reversal

        print("\n>> Demo 1: Positive Narrative Bubble")
        run_demo_positive_narrative(output_dir=output_dir, steps=300)

        print("\n>> Demo 2: Regulatory Shock & Panic")
        run_demo_regulatory_shock(output_dir=output_dir, steps=300)

        print("\n>> Demo 3: Narrative Reversal & Bubble Burst")
        run_demo_narrative_reversal(output_dir=output_dir, steps=400)

        print("\n[OK] All V0.2 demos complete!")
        print(f"[DIR] Results saved to: {output_dir}/")

    elif "--demo" in args:
        idx = None
        try:
            idx = int(args[args.index("--demo") + 1])
        except (IndexError, ValueError):
            pass

        demos = {
            1: ("Positive Narrative Bubble",
                "experiments.demo_positive_narrative", "run_demo_positive_narrative", 300),
            2: ("Regulatory Shock & Panic",
                "experiments.demo_regulatory_shock", "run_demo_regulatory_shock", 300),
            3: ("Narrative Reversal & Bubble Burst",
                "experiments.demo_narrative_reversal", "run_demo_narrative_reversal", 400),
        }

        if idx and idx in demos:
            name, module, func_name, steps = demos[idx]
            print(f">> Running Demo {idx}: {name}")
            mod = __import__(module, fromlist=[func_name])
            getattr(mod, func_name)(output_dir=output_dir, steps=steps)
        else:
            print("Available demos: --demo 1 / --demo 2 / --demo 3")
            print("Or use --v02 to run all V0.2 demos")

    elif "--herding" in args:
        from experiments.herding_ablation import run_herding_experiment
        run_herding_experiment(output_dir=output_dir)

    elif "--blackswan" in args:
        from experiments.black_swan import run_black_swan_experiment
        run_black_swan_experiment(output_dir=output_dir)

    elif "--help" in args or "-h" in args:
        print(__doc__)

    else:
        # ???? V0.1 ??????
        print("=" * 60)
        print("FundGenesis V0.1 ? Running Default (Emotion Shock)")
        print("(Use --v02 for ReflexMarket-AI demos)")
        print("=" * 60)
        from experiments.emotion_shock import run_emotion_shock_experiment
        run_emotion_shock_experiment(output_dir=output_dir)
        print(f"\n[OK] Results saved to: {output_dir}/")


if __name__ == "__main__":
    main()
