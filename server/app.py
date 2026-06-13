"""FastAPI app — serves the dashboard and bridges the game over WebSocket.

STUB skeleton. The browser runs jsnes and the dashboard; it connects here over
WebSocket. The harness sends actions; the browser returns game state + frames.
Build out the WS protocol and wire HarnessLoop to a WebSocket-backed adapter.
"""
from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI, WebSocket
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:  # fastapi optional until server work begins
    FastAPI = None  # type: ignore

STATIC = Path(__file__).parent / "static"


def create_app():
    if FastAPI is None:
        raise RuntimeError("fastapi not installed — pip install -r requirements.txt")

    app = FastAPI(title="Gauntlet — Joypad Harness")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        # TODO(ralph): WS protocol — browser sends game state, harness sends
        # actions; stream checkpoint/alarm/guardrail events to the dashboard.
        await socket.close()

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
