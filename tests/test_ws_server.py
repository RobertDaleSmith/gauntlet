"""WebSocket protocol test via FastAPI TestClient (no browser)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from server.app import create_app  # noqa: E402


def _state(height, lines=0, game_over=False, frame=0):
    return {"frame": frame, "stack_height": height, "lines": lines,
            "score": lines * 100, "holes": 0, "game_over": game_over, "level": 1}


def test_ws_returns_actions_and_grades():
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "observe", "state": _state(0)})
        first = ws.receive_json()
        assert first["type"] == "act"
        assert first["action"]["buttons"]

        ws.send_json({"type": "observe", "state": _state(15, frame=4), "frame": "data:img"})
        second = ws.receive_json()
        # graded the prior step; stack-too-high alarm present
        assert any(c["name"] == "STACK_HEIGHT_SAFE" for c in second["checkpoints"])
        assert any(a["type"] == "CHECKPOINT_FAILED" for a in second.get("alarms", []))


def test_ws_worker_swap():
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "set_worker", "worker": "scripted"})
        assert ws.receive_json() == {
            "type": "worker_set", "worker": "scripted", "model": None, "perception": None
        }


def test_ws_set_claude_model_and_perception():
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "set_worker", "worker": "claude",
                      "model": "claude-opus-4-8", "perception": "text"})
        assert ws.receive_json() == {
            "type": "worker_set", "worker": "claude",
            "model": "claude-opus-4-8", "perception": "text",
        }


def test_replay_endpoint_returns_persisted_steps(tmp_path):
    import server.app as appmod
    appmod.DB_PATH = str(tmp_path / "runs.db")
    client = TestClient(appmod.create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "observe", "state": _state(0)})
        first = ws.receive_json()
        run_id = first["run_id"]
        ws.send_json({"type": "observe", "state": _state(2, frame=4)})
        ws.receive_json()
    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert len(body["steps"]) >= 1


def test_ws_reset_starts_fresh():
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "observe", "state": _state(2)})
        ws.receive_json()
        ws.send_json({"type": "reset"})
        assert ws.receive_json() == {"type": "reset_ok"}
        ws.send_json({"type": "observe", "state": _state(0)})
        out = ws.receive_json()
        assert out["type"] == "act" and out["checkpoints"] == []  # fresh session
