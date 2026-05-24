#!/bin/bash
# FundGenesis - Quick Start Script (Linux/macOS)
# Usage: bash start.sh [demo|monitor|dashboard]

set -e

cd "$(dirname "$0")"

DEMO=${1:-""}

echo "============================================"
echo "FundGenesis - ReflexMarket-AI"
echo "============================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ] && [ ! -f "requirements.txt" ]; then
    echo "[WARN] No venv or requirements.txt found, assuming dependencies installed"
fi

case "$DEMO" in
    1)
        echo "Running Demo 1: Positive Narrative Bubble..."
        python3 experiments/demo_positive_narrative.py
        ;;
    2)
        echo "Running Demo 2: Regulatory Shock & Panic..."
        python3 experiments/demo_regulatory_shock.py
        ;;
    3)
        echo "Running Demo 3: Narrative Reversal & Bubble Burst..."
        python3 experiments/demo_narrative_reversal.py
        ;;
    monitor)
        echo "Starting Reflexivity Monitor (WebSocket Dashboard) on port 8765..."
        python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8765 --reload
        ;;
    all)
        echo "Running ALL experiments..."
        python3 main.py --v02
        ;;
    "")
        echo "Starting interactive dashboard (Demo 3)..."
        python3 dashboard_runner.py --demo 3
        ;;
    help|--help|-h)
        echo "Usage: bash start.sh [demo|monitor|dashboard|all]"
        echo ""
        echo "Commands:"
        echo "  (none)   Run dashboard + Demo 3 (default)"
        echo "  1        Run Demo 1: Positive Narrative Bubble"
        echo "  2        Run Demo 2: Regulatory Shock & Panic"
        echo "  3        Run Demo 3: Narrative Reversal & Bubble Burst"
        echo "  monitor  Start WebSocket dashboard server (port 8765)"
        echo "  all      Run all V0.2 demos"
        echo "  help     Show this help message"
        ;;
    *)
        echo "[ERROR] Unknown command: $DEMO"
        echo "Run 'bash start.sh help' for usage"
        exit 1
        ;;
esac
