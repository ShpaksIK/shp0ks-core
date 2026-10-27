import asyncio
import json

from core.paths import CONFIG_PATH

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from core.registry import registry
from core.services.monitor import monitor

from core.api import modules as api_modules
from core.api import monitor as api_monitor
from core.api import launcher as api_launcher
from core.api import vault as api_vault
from core.api import script_runner as api_script_runner
from core.api import voice as api_voice


_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
HISTORY_INTERVAL = _config.get("monitor", {}).get("history_interval_seconds", 300)


app = FastAPI(title="shp0ks Core")
app.include_router(api_modules.router)
app.include_router(api_monitor.router)
app.include_router(api_launcher.router)
app.include_router(api_vault.router)
app.include_router(api_script_runner.router)
app.include_router(api_voice.router)


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/monitor/stream")
async def monitor_stream(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.on_event("startup")
async def start_background_tasks():
    async def broadcast_loop():
        while True:
            if registry.is_enabled("monitor"):
                snapshot = monitor.get_snapshot()
                await manager.broadcast(snapshot)
            await asyncio.sleep(1.0)

    async def history_loop():
        while True:
            if registry.is_enabled("monitor"):
                monitor.save_snapshot()
            await asyncio.sleep(HISTORY_INTERVAL)

    asyncio.create_task(broadcast_loop())
    asyncio.create_task(history_loop())


@app.get("/health")
def health():
    return {"status": "OK"}
