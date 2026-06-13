"""Claude worker — Anthropic SDK, structured-output *button* actions.

Two perception modes, both drive the controller like a human (LEFT/RIGHT/ROTATE/
DROP — never abstract placements):

- "text"  (default): the board is given as a compact ASCII grid. Fast (no image
  tokens) and accurate — the model actually clears lines. ~sub-second on Haiku.
- "vision": the board is given as the rendered frame (an image). Most human-like
  ("it sees the screen"), but slower and weaker.

The agent plans the whole placement for the current piece in one turn and returns
the button sequence ending in DROP. Client is injectable for tests.
"""
from __future__ import annotations

import json

from harness.types import Action, GameState

MODEL = "claude-haiku-4-5"  # fast (~1s/piece)

SYSTEM = (
    "You are playing Tetris and driving the controller. The board is 10 wide, 20 "
    "tall. Plan where the CURRENT falling piece should land to keep the stack low "
    "and flat, avoid burying holes, and complete full rows. Output the controller "
    "sequence to get it there: zero or more ROTATE, then move with LEFT or RIGHT "
    "(never both in one turn), then a final DROP. Always end with DROP so the piece "
    "locks. If feedback says the stack is too high, prioritize clearing lines."
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


def _render_board(state: GameState) -> str:
    """Compact ASCII board: @ = falling piece, # = filled, . = empty."""
    board = state.raw.get("board")
    if not board:
        return "(board unavailable)"
    cur = {tuple(c) for c in state.raw.get("current", {}).get("cells", [])}
    header = "  " + "".join(str(c % 10) for c in range(len(board[0])))
    lines = [header]
    for r, row in enumerate(board):
        cells = "".join(
            "@" if (r, c) in cur else ("#" if v else ".") for c, v in enumerate(row)
        )
        lines.append(f"  {cells}")
    return "\n".join(lines)


class ClaudeWorker:
    name = "claude"

    def __init__(self, client=None, model: str = MODEL, perception: str = "text") -> None:
        self.client = client
        self.model = model
        self.perception = perception
        self._frame: str | None = None

    def set_frame(self, frame: str | None) -> None:
        """Latest rendered frame (data URL) — used only in vision perception mode."""
        self._frame = frame

    def _ensure_client(self):
        if self.client is None:
            import anthropic  # lazy: package only needed when actually running

            self.client = anthropic.Anthropic()
        return self.client

    def _content(self, state: GameState, feedback: str | None):
        instr = (
            f"feedback: {feedback or 'none'}\n"
            "Output the button sequence to place the falling piece "
            "(rotations, then LEFT or RIGHT, then DROP)."
        )
        if self.perception == "vision" and self._frame:
            b64 = self._frame.split(",", 1)[1] if "," in self._frame else self._frame
            return [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": instr},
            ]
        # text perception (default)
        next_piece = state.raw.get("next", "?")
        return (
            f"Board (next piece: {next_piece}):\n{_render_board(state)}\n\n{instr}"
        )

    def decide(self, state: GameState, feedback: str | None) -> Action:
        resp = self._ensure_client().messages.create(
            model=self.model,
            max_tokens=256,
            system=SYSTEM,
            messages=[{"role": "user", "content": self._content(state, feedback)}],
            output_config={"format": {"type": "json_schema", "schema": ACTION_SCHEMA}},
        )
        text = next(b.text for b in resp.content if getattr(b, "type", None) == "text")
        data = json.loads(text)
        return Action(tuple(data["buttons"]), int(data["hold_frames"]))
