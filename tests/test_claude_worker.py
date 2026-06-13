"""ClaudeWorker test with a mock client — no API key / anthropic package needed."""
from harness.types import GameState
from workers.claude import MODEL, ClaudeWorker


class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Resp:
    def __init__(self, text):
        self.content = [_Block(text)]


class FakeClient:
    """Stands in for anthropic.Anthropic(); records the call, returns canned JSON."""

    def __init__(self, text):
        self._text = text
        self.last_kwargs = None
        self.messages = self

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _Resp(self._text)


def test_claude_worker_parses_structured_action():
    fake = FakeClient('{"buttons": ["RIGHT", "A"], "hold_frames": 24}')
    worker = ClaudeWorker(client=fake)
    action = worker.decide(GameState(0, x=400), feedback="stuck, try jump")
    assert action.buttons == ("RIGHT", "A")
    assert action.hold_frames == 24


def test_claude_worker_uses_haiku_and_passes_feedback():
    fake = FakeClient('{"buttons": ["RIGHT"], "hold_frames": 30}')
    ClaudeWorker(client=fake).decide(GameState(0), feedback="hello-feedback")
    assert fake.last_kwargs["model"] == MODEL
    prompt = fake.last_kwargs["messages"][0]["content"]
    assert "hello-feedback" in prompt
