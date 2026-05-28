"""
dashboard/app.py
=================
FundGenesis REST API + WebSocket Dashboard Server

REST API Endpoints:
  GET  /                     - Service info
  GET  /health               - Health check
  POST /api/v1/simulation/run      - Run a simulation
  GET  /api/v1/simulation/{id}     - Get simulation results
  GET  /api/v1/simulation/{id}/steps - Get step-by-step data
  POST /api/v1/narrative/inject    - Inject a narrative event
  GET  /api/v1/market/state        - Get current market state
  GET  /api/v1/agents/summary      - Get agent population summary
  WS   /ws                         - WebSocket for real-time data
"""

import asyncio
import json
import time
import uuid
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

logger = logging.getLogger('FundGenesis.dashboard')

app = FastAPI(
    title="FundGenesis API",
    description="Financial Reflexivity Multi-Agent Simulation Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Data Models ============

class SimulationRequest(BaseModel):
    """Request to run a simulation"""
    n_steps: int = Field(default=200, ge=10, le=5000, description="Number of simulation steps")
    n_retail: int = Field(default=50, ge=1, le=500, description="Number of retail agents")
    n_trend: int = Field(default=20, ge=0, le=200, description="Number of trend follower agents")
    n_value: int = Field(default=10, ge=0, le=100, description="Number of value investor agents")
    initial_price: float = Field(default=100.0, gt=0, description="Initial asset price")
    fundamental_value: float = Field(default=100.0, gt=0, description="Fundamental value")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    narrative_events: List[Dict] = Field(default_factory=list, description="Narrative events to inject")
    shocks: List[Dict] = Field(default_factory=list, description="External shocks")
    enable_reflexivity_game: bool = Field(default=True, description="Enable game theory analysis")
    enable_risk_propagation: bool = Field(default=True, description="Enable risk propagation")
    enable_regulator: bool = Field(default=True, description="Enable regulatory agent")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "n_steps": 100,
                    "n_retail": 30,
                    "n_trend": 15,
                    "n_value": 5,
                    "initial_price": 100.0,
                    "seed": 42,
                    "narrative_events": [
                        {
                            "name": "Tech Boom",
                            "category": "fintech",
                            "polarity": "positive",
                            "intensity": 0.7,
                            "timing": 20,
                            "duration": 30,
                        }
                    ],
                }
            ]
        }
    }


class NarrativeInjectRequest(BaseModel):
    """Request to inject a narrative event"""
    name: str = Field(description="Narrative name")
    category: str = Field(default="sentiment", description="Category: policy, sector, macro, fintech, regulatory, earnings")
    polarity: str = Field(description="positive, negative, or neutral")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="Narrative intensity")
    credibility: float = Field(default=0.6, ge=0.0, le=1.0, description="Narrative credibility")
    duration: int = Field(default=20, ge=1, le=200, description="Duration in steps")


class SimulationSummary(BaseModel):
    """Summary of a simulation"""
    id: str
    status: str
    n_steps: int
    final_price: Optional[float] = None
    total_return: Optional[float] = None
    max_bubble_risk: Optional[float] = None
    max_panic_risk: Optional[float] = None
    duration_seconds: Optional[float] = None
    created_at: str


# ============ State Management ============

class AppState:
    def __init__(self):
        self.simulations: Dict[str, Dict] = {}
        self.active_runners: Dict[str, Any] = {}
        self.market_state: Dict[str, Any] = {
            "price": 100.0,
            "fear": 0.3,
            "greed": 0.3,
            "reflexivity_index": 0.0,
            "bubble_risk": 0.0,
            "regime": "normal",
        }
        self.narrative_log: List[Dict] = []

state = AppState()


# ============ WebSocket Manager ============

class DashboardServer:
    def __init__(self):
        self.connections: list = []
        self.latest_data: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
        if self.latest_data:
            await websocket.send_json(self.latest_data)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, data: Dict[str, Any]):
        self.latest_data = data
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

dashboard_server = DashboardServer()


# ============ REST API Endpoints ============

@app.get("/")
async def root():
    """Service information"""
    return {
        "service": "FundGenesis API",
        "description": "Financial Reflexivity Multi-Agent Simulation Platform",
        "version": "1.0.0",
        "endpoints": {
            "simulation": "/api/v1/simulation/run",
            "narrative": "/api/v1/narrative/inject",
            "market": "/api/v1/market/state",
            "agents": "/api/v1/agents/summary",
            "websocket": "/ws",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "connections": len(dashboard_server.connections),
        "simulations": len(state.simulations),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/v1/simulation/run")
async def run_simulation(request: SimulationRequest):
    """
    Run a financial market simulation.

    Returns simulation ID and results including:
    - Price trajectory
    - Risk metrics
    - Agent behavior statistics
    - Game theory analysis
    - Risk propagation data
    """
    sim_id = str(uuid.uuid4())[:8]

    try:
        from core.simulation_runner import SimulationRunner, SimulationConfig

        config = SimulationConfig(
            n_steps=request.n_steps,
            n_retail=request.n_retail,
            n_trend=request.n_trend,
            n_value=request.n_value,
            initial_price=request.initial_price,
            fundamental_value=request.fundamental_value,
            seed=request.seed,
            narrative_events=request.narrative_events,
            shocks=request.shocks,
            enable_reflexivity_game=request.enable_reflexivity_game,
            enable_risk_propagation=request.enable_risk_propagation,
            enable_regulator=request.enable_regulator,
            quiet=True,
        )

        runner = SimulationRunner(config)
        result = runner.run()

        # Store results
        state.simulations[sim_id] = {
            "id": sim_id,
            "status": "completed",
            "request": request.model_dump(),
            "result": result.as_dict(),
            "created_at": datetime.now().isoformat(),
        }

        # Update market state with final values
        if result.steps:
            last = result.steps[-1]
            state.market_state = {
                "price": last.price,
                "fear": last.fear,
                "greed": last.greed,
                "reflexivity_index": last.reflexivity_index,
                "bubble_risk": last.bubble_risk,
                "panic_risk": last.panic_risk,
                "regime": last.regime,
            }

        # Broadcast via WebSocket
        await dashboard_server.broadcast({
            "type": "simulation_complete",
            "simulation_id": sim_id,
            "summary": {
                "final_price": result.final_price,
                "total_return": result.total_return,
                "max_bubble_risk": result.max_bubble_risk,
                "max_panic_risk": result.max_panic_risk,
                "regime_distribution": result.regime_distribution,
            },
        })

        return {
            "simulation_id": sim_id,
            "status": "completed",
            "summary": {
                "final_price": round(result.final_price, 2),
                "total_return": round(result.total_return, 4),
                "max_bubble_risk": round(result.max_bubble_risk, 4),
                "max_panic_risk": round(result.max_panic_risk, 4),
                "peak_price": round(result.peak_price, 2),
                "trough_price": round(result.trough_price, 2),
                "duration_seconds": round(result.duration_seconds, 2),
                "regime_distribution": result.regime_distribution,
            },
            "n_steps": len(result.steps),
            "detail_url": f"/api/v1/simulation/{sim_id}",
        }

    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@app.get("/api/v1/simulation/{simulation_id}")
async def get_simulation(simulation_id: str):
    """Get simulation results by ID"""
    if simulation_id not in state.simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return state.simulations[simulation_id]


@app.get("/api/v1/simulation/{simulation_id}/steps")
async def get_simulation_steps(simulation_id: str,
                                offset: int = 0,
                                limit: int = 100):
    """Get step-by-step simulation data with pagination"""
    if simulation_id not in state.simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = state.simulations[simulation_id]
    steps = sim.get("result", {}).get("steps", [])
    total = len(steps)

    return {
        "simulation_id": simulation_id,
        "total_steps": total,
        "offset": offset,
        "limit": limit,
        "steps": steps[offset:offset + limit],
    }


@app.post("/api/v1/narrative/inject")
async def inject_narrative(request: NarrativeInjectRequest):
    """
    Inject a narrative event into the current market state.

    This is a simulation-only endpoint - it records the narrative
    for use in the next simulation run.
    """
    from narrative.narrative_event import Polarity, NarrativeCategory

    try:
        polarity = Polarity(request.polarity)
        category = NarrativeCategory(request.category)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")

    event_record = {
        "name": request.name,
        "category": request.category,
        "polarity": request.polarity,
        "intensity": request.intensity,
        "credibility": request.credibility,
        "duration": request.duration,
        "injected_at": datetime.now().isoformat(),
    }
    state.narrative_log.append(event_record)

    await dashboard_server.broadcast({
        "type": "narrative_injected",
        "narrative": event_record,
    })

    return {
        "status": "injected",
        "narrative": event_record,
        "message": "Narrative will be included in next simulation run",
    }


@app.get("/api/v1/market/state")
async def get_market_state():
    """Get current market state snapshot"""
    return {
        "market": state.market_state,
        "active_simulations": len(state.active_runners),
        "total_simulations": len(state.simulations),
        "narrative_log_size": len(state.narrative_log),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/agents/summary")
async def get_agents_summary():
    """Get agent population summary and statistics"""
    return {
        "agent_types": {
            "emotional_retail": {
                "description": "情绪化散户 - FOMO驱动，高羊群效应",
                "emotional_sensitivity": 0.8,
                "herding_coefficient": 0.7,
                "narrative_sensitivity": 0.12,
            },
            "trend_follower": {
                "description": "趋势跟踪者 - 动量驱动，中等羊群效应",
                "emotional_sensitivity": 0.4,
                "herding_coefficient": 0.4,
                "narrative_sensitivity": 0.06,
            },
            "value_investor": {
                "description": "价值投资者 - 基本面驱动，低羊群效应",
                "emotional_sensitivity": 0.2,
                "herding_coefficient": 0.1,
                "narrative_sensitivity": 0.03,
            },
        },
        "network_structure": {
            "kol_tiers": ["macro", "influencer", "micro", "retail"],
            "propagation_model": "KOL -> Influencer -> Micro -> Retail",
            "decay_factor": 0.3,
        },
        "reflexivity_model": {
            "causal_chain": "Narrative -> Belief -> Emotion -> Behavior -> Capital -> Price",
            "feedback": "Price -> Narrative Confirmation/Falsification",
        },
    }


@app.get("/api/v1/simulations")
async def list_simulations():
    """List all simulation results"""
    summaries = []
    for sid, sim in state.simulations.items():
        result = sim.get("result", {})
        summary_data = result.get("summary", {})
        summaries.append({
            "id": sid,
            "status": sim.get("status", "unknown"),
            "n_steps": result.get("config", {}).get("n_steps", 0),
            "final_price": summary_data.get("final_price"),
            "total_return": summary_data.get("total_return"),
            "max_bubble_risk": summary_data.get("max_bubble_risk"),
            "created_at": sim.get("created_at"),
        })
    return {"simulations": summaries}


# ============ WebSocket Endpoint ============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time simulation data"""
    await dashboard_server.connect(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "time": time.time()})
                elif msg.get("type") == "get_state":
                    await websocket.send_json({
                        "type": "market_state",
                        "data": state.market_state,
                    })
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat", "time": time.time()})
    except WebSocketDisconnect:
        dashboard_server.disconnect(websocket)
    except Exception:
        dashboard_server.disconnect(websocket)


# ============ Standalone Mode ============

def run_dashboard(port: int = 8765):
    """Run dashboard server"""
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"FundGenesis API starting on port {args.port}...")
    print(f"API docs: http://localhost:{args.port}/docs")
    run_dashboard(port=args.port)
