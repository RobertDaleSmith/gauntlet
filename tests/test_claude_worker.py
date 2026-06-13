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
    fake = FakeClient('{"buttons": ["LEFT", "DROP"], "hold_frames": 4}')
    worker = ClaudeWorker(client=fake)
    action = worker.decide(GameState(0), feedback="stack too high")
    assert action.buttons == ("LEFT", "DROP")
    assert action.hold_frames == 4


def test_claude_worker_uses_haiku_and_passes_feedback():
    fake = FakeClient('{"buttons": ["DROP"], "hold_frames": 4}')
    ClaudeWorker(client=fake).decide(GameState(0), feedback="hello-feedback")
    assert fake.last_kwargs["model"] == MODEL
    # feedback is carried in the user message (text or vision content list)
    assert "hello-feedback" in str(fake.last_kwargs["messages"])


def test_claude_vision_mode_sends_frame_as_image():
    fake = FakeClient('{"buttons": ["DROP"], "hold_frames": 4}')
    w = ClaudeWorker(client=fake, perception="vision")
    w.set_frame("data:image/png;base64,AAAABBBB")  # the rendered frame
    w.decide(GameState(0), feedback=None)
    content = fake.last_kwargs["messages"][0]["content"]
    assert isinstance(content, list)
    image = next(b for b in content if b.get("type") == "image")
    assert image["source"]["data"] == "AAAABBBB"  # base64 prefix stripped


def test_claude_text_mode_renders_ascii_board():
    fake = FakeClient('{"buttons": ["LEFT", "DROP"], "hold_frames": 4}')
    board = [[0] * 10 for _ in range(20)]
    board[19][0] = 1  # one filled cell, bottom-left
    state = GameState(0, raw={"board": board, "current": {"cells": [[0, 4]]}, "next": "I"})
    ClaudeWorker(client=fake, perception="text").decide(state, feedback=None)
    content = fake.last_kwargs["messages"][0]["content"]
    assert isinstance(content, str)
    assert "#" in content and "@" in content and "next piece: I" in content
