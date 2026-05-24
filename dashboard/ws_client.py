"""
WebSocket client that connects to the FundGenesis simulation
and forwards data to the dashboard for real-time visualization.
"""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import websocket
except ImportError:
    print("Installing websocket-client...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
    import websocket


WS_URL = "ws://localhost:8765/ws"


class WsDashboardClient:
    """Sends simulation data to the web dashboard via WebSocket."""

    def __init__(self, url: str = WS_URL):
        self.url = url
        self.ws = None
        self.connected = False

    def connect(self):
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            print(f"[Dashboard] Connecting to {self.url}...")
            self.ws.run_forever(ping_interval=10)
        except Exception as e:
            print(f"[Dashboard] Connection error: {e}")

    def _on_open(self, ws):
        self.connected = True
        print("[Dashboard] Connected!")

    def _on_message(self, ws, message):
        pass  # We don't process messages from dashboard for now

    def _on_error(self, ws, error):
        print(f"[Dashboard] Error: {error}")

    def _on_close(self, ws, code, reason):
        self.connected = False
        print(f"[Dashboard] Disconnected: {code} {reason}")

    def send(self, data: dict):
        """Send simulation data to dashboard."""
        if self.connected and self.ws:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                print(f"[Dashboard] Send error: {e}")
                self.connected = False


def run_client():
    client = WsDashboardClient()
    try:
        client.connect()
    except KeyboardInterrupt:
        print("\n[Dashboard] Client stopped.")


if __name__ == "__main__":
    run_client()
