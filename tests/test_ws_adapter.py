"""WebSocketGameAdapter is a drop-in GameAdapter (no harness changes)."""
from harness.adapters import FakeGameAdapter, WebSocketGameAdapter
from harness.loop import HarnessLoop
from harness.types import Action
from workers.scripted import ScriptedWorker


class RecordingTransport:
    """Records sent messages; delegates to a FakeGameAdapter for realistic state."""

    def __init__(self):
        self.adapter = FakeGameAdapter()
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
    a.execute(Action(("RIGHT", "A"), 30), None)
    assert t.sent[0]["type"] == "read_state"
    assert t.sent[1] == {"type": "execute", "buttons": ["RIGHT", "A"], "hold_frames": 30}


def test_ws_adapter_is_loop_compatible():
    # Same loop, same worker — only the adapter changed. Hero beat still clears.
    loop = HarnessLoop(WebSocketGameAdapter(RecordingTransport()), ScriptedWorker())
    loop.run(max_steps=20)
    assert loop.state.x > FakeGameAdapter.PIPE_X + 10
    assert loop.status == "RUNNING"
