"""Claude worker — Anthropic SDK, Haiku 4.5, structured-output actions.

Reads structured GameState, returns an Action via structured output
(`{buttons, hold_frames}`). Haiku is the fast reflex layer, so thinking is left
off for latency. The client is injectable for testing; in production it lazily
constructs `anthropic.Anthropic()`.
"""
from __future__ import annotations

import json

from harness.types import Action, GameState

MODEL = "claude-haiku-4-5"

SYSTEM = (
    "You are playing Tetris through a controller. You SEE the board as an image. "
    "Return the next controller action: which buttons to hold and for how long. "
    "Buttons: LEFT, RIGHT, ROTATE, DOWN, DROP. Keep the stack low and flat, avoid "
    "holes, and clear lines. If feedback says the stack is too high, reposition "
    "the piece (LEFT/RIGHT/ROTATE) to fill gaps rather than dropping straight down."
)

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "buttons": {"type": "array", "items": {"type": "string"}},
        "hold_frames": {"type": "integer"},
    },
    "required": ["buttons", "hold_frames"],
    "additionalProperties": False,
}


class ClaudeWorker:
    name = "claude"

    def __init__(self, client=None, model: str = MODEL) -> None:
        self.client = client
        self.model = model
        self._frame: str | None = None

    def set_frame(self, frame: str | None) -> None:
        """Latest rendered frame (data URL). The session calls this before decide;
        this is the agent's only perception channel — it sees pixels, like a human."""
        self._frame = frame

    def _ensure_client(self):
        if self.client is None:
            import anthropic  # lazy: package only needed when actually running

            self.client = anthropic.Anthropic()
        return self.client

    def _prompt(self, feedback: str | None) -> str:
        # Text carries only the coach's feedback hint — never the ground-truth
        # board the referee uses to grade. The agent reads the board from the image.
        return f"feedback: {feedback or 'none'}\nReturn the next controller action."

    def _content(self, feedback: str | None):
        text = {"type": "text", "text": self._prompt(feedback)}
        if not self._frame:
            return self._prompt(feedback)  # text-only fallback (no frame yet)
        b64 = self._frame.split(",", 1)[1] if "," in self._frame else self._frame
        image = {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64},
        }
        return [image, text]

    def decide(self, state: GameState, feedback: str | None) -> Action:
        resp = self._ensure_client().messages.create(
            model=self.model,
            max_tokens=256,
            system=SYSTEM,
            messages=[{"role": "user", "content": self._content(feedback)}],
            output_config={"format": {"type": "json_schema", "schema": ACTION_SCHEMA}},
        )
        text = next(b.text for b in resp.content if getattr(b, "type", None) == "text")
        data = json.loads(text)
        return Action(tuple(data["buttons"]), int(data["hold_frames"]))
