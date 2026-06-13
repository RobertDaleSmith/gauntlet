"""Claude worker — Anthropic SDK, vision, structured-output actions.

The agent SEES the rendered board as an image and plans a whole placement for the
current piece in one turn (look once, output the full button sequence ending in
DROP) — far fewer vision calls than nudging one button at a time. Uses Opus 4.8
(strong high-res vision) with adaptive thinking. Client is injectable for tests.
"""
from __future__ import annotations

import json

from harness.types import Action, GameState

MODEL = "claude-opus-4-8"

SYSTEM = (
    "You are playing Tetris. You SEE the current board as an image: a 10-wide, "
    "20-tall grid; filled cells are colored, the falling piece is at the top. "
    "Plan where the CURRENT piece should land to keep the stack low and flat, "
    "avoid burying holes, and complete full rows. Then output the controller "
    "sequence to get it there: zero or more ROTATE, then move horizontally with "
    "LEFT *or* RIGHT (never both in one turn), then a final DROP. Always end with "
    "DROP so the piece locks this turn. If feedback says the stack is too high, "
    "prioritize flattening and clearing lines."
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
        return (
            f"feedback: {feedback or 'none'}\n"
            "Output the button sequence to place the current piece (rotations, "
            "then LEFT or RIGHT moves, then DROP)."
        )

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
            max_tokens=2048,
            system=SYSTEM,
            messages=[{"role": "user", "content": self._content(feedback)}],
            thinking={"type": "adaptive"},  # let it plan the placement
            output_config={
                "format": {"type": "json_schema", "schema": ACTION_SCHEMA},
                "effort": "low",  # quick planning; the game waits, so no drift
            },
        )
        text = next(b.text for b in resp.content if getattr(b, "type", None) == "text")
        data = json.loads(text)
        return Action(tuple(data["buttons"]), int(data["hold_frames"]))
