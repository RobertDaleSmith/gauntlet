"""FastAPI app — serves the game + dashboard and bridges them over WebSocket.

The browser renders Tetris and the dashboard. Each step it sends an `observe`
(ground-truth state + rendered frame); a per-connection `HarnessSession` runs the
pillars and returns the next `act` (controller action) plus the events to display.
`set_worker` swaps the agent live; `reset` starts a fresh run. `GET /api/runs/{id}`
replays a persisted run.
"""
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a repo-root .env into the environment.

    Lets the vision worker pick up ANTHROPIC_API_KEY without exporting it in the
    shell that launches the server. Existing env vars win (setdefault).
    """
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:  # fastapi optional until server work begins
    FastAPI = None  # type: ignore

STATIC = Path(__file__).parent / "static"
# File-backed so runs persist for replay across HTTP requests.
DB_PATH = str(Path(__file__).resolve().parent.parent / ".runs.db")


def _make_worker(name: str):
    from workers.scripted import ScriptedWorker

    if name == "claude":
        from workers.claude import ClaudeWorker

        return ClaudeWorker()
    if name == "heuristic":
        from workers.heuristic import HeuristicWorker

        return HeuristicWorker()
    return ScriptedWorker()


def create_app():
    if FastAPI is None:
        raise RuntimeError("fastapi not installed — pip install -r requirements.txt")

    _load_dotenv()  # pick up ANTHROPIC_API_KEY from .env if present

    from harness.material import MaterialHandler
    from harness.session import HarnessSession

    app = FastAPI(title="Gauntlet — Joypad Harness")

    @app.get("/api/runs/{run_id}")
    def replay(run_id: str):
        """Replay a finished run from persisted checkpoints (the Material pillar)."""
        return {"run_id": run_id, "steps": MaterialHandler(DB_PATH).replay(run_id)}

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        session = HarnessSession(db_path=DB_PATH)
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
                    session = HarnessSession(session.loop.worker, db_path=DB_PATH)
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
