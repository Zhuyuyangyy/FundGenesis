"""
FundGenesis WebSocket Dashboard Server
实时可视化仪表盘 - 通过WebSocket推送仿真数据
"""

import asyncio
import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="FundGenesis Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ WebSocket Manager ============

class DashboardServer:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.latest_data: Dict[str, Any] = {}
        self.running = False

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
        # Send current state on connect
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

    def push_data(self, data: Dict[str, Any]):
        """Thread-safe push from simulation thread"""
        asyncio.create_task(self.broadcast(data))


dashboard_server = DashboardServer()


# ============ REST API ============

@app.get("/")
async def root():
    return {
        "service": "FundGenesis WebSocket Dashboard",
        "version": "1.0.0",
        "websocket": "/ws",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "connections": len(dashboard_server.connections)}


# ============ WebSocket Endpoint ============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await dashboard_server.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "time": time.time()})
            except asyncio.TimeoutError:
                # Send heartbeat
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
    print(f"FundGenesis Dashboard starting on port {args.port}...")
    run_dashboard(port=args.port)
