"""WebSocketGameAdapter is a drop-in GameAdapter (no harness changes)."""
from harness.adapters import FakeTetrisAdapter, WebSocketGameAdapter
from harness.loop import HarnessLoop
from harness.types import Action
from workers.scripted import ScriptedWorker


class RecordingTransport:
    """Records sent messages; delegates to a FakeTetrisAdapter for real state."""

    def __init__(self):
        self.adapter = FakeTetrisAdapter()
        self.sent = []

    def request(self, message: dict) -> dict:
        self.sent.append(message)
        t = message["type"]
        if t == "read_state":
            return self.adapter.read_state()
        if t == "reset":
            self.adapter.reset()
            return self.adapter.read_state()
        if t == "execute":
            return self.adapter.execute(
                Action(tuple(message["buttons"]), message["hold_frames"]), None
            )
        raise ValueError(t)


def test_adapter_sends_typed_messages():
    t = RecordingTransport()
    a = WebSocketGameAdapter(t)
    a.read_state()
    a.execute(Action(("LEFT", "DROP"), 4), None)
    assert t.sent[0]["type"] == "read_state"
    assert t.sent[1] == {"type": "execute", "buttons": ["LEFT", "DROP"], "hold_frames": 4}


def test_ws_adapter_is_loop_compatible():
    # Same loop, same worker — only the adapter changed. Hero beat still works.
    loop = HarnessLoop(WebSocketGameAdapter(RecordingTransport()), ScriptedWorker())
    loop.run(max_steps=30)
    assert loop.state.lines >= 1
    assert loop.status == "RUNNING"
