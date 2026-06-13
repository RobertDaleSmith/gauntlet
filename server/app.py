"""FastAPI app — serves the dashboard and bridges the game over WebSocket.

STUB skeleton. The browser runs jsnes and the dashboard; it connects here over
WebSocket. The harness sends actions; the browser returns game state + frames.
Build out the WS protocol and wire HarnessLoop to a WebSocket-backed adapter.
"""
from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:  # fastapi optional until server work begins
    FastAPI = None  # type: ignore

STATIC = Path(__file__).parent / "static"


def _make_worker(name: str):
    from workers.scripted import ScriptedWorker

    if name == "claude":
        from workers.claude import ClaudeWorker

        return ClaudeWorker()
    return ScriptedWorker()


def create_app():
    if FastAPI is None:
        raise RuntimeError("fastapi not installed — pip install -r requirements.txt")

    from harness.session import HarnessSession

    app = FastAPI(title="Gauntlet — Joypad Harness")

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        session = HarnessSession()
        try:
            while True:
                msg = await socket.receive_json()
                kind = msg.get("type")
                if kind == "observe":
                    out = session.step(msg.get("state", {}), msg.get("frame"))
                    await socket.send_json(out)
                elif kind == "set_worker":
                    session.set_worker(_make_worker(msg.get("worker", "scripted")))
                    await socket.send_json({"type": "worker_set", "worker": msg.get("worker")})
                elif kind == "reset":
                    session = HarnessSession(session.loop.worker)
                    await socket.send_json({"type": "reset_ok"})
        except WebSocketDisconnect:
            return

    # Serve the game + dashboard at root (index.html uses relative paths, so it
    # works the same opened as a file or served here).
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
