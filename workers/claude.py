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

# --- "json" perception: structured board in, full plan out, one step ahead ---
# Pure-planner experiment: no local candidate enumeration or move scoring. The
# model gets a JSON board (occupancy grid + current/next pieces) and must plan
# the placement itself, then state its intended plan for the NEXT piece. We feed
# that intent back the following turn so it can keep or revise — receding-horizon
# planning driven entirely by the model.
PLAN_SYSTEM = (
    "You are playing Tetris by driving a controller. The board is a JSON grid, "
    "10 columns wide and 20 rows tall; row 0 is the TOP, row 19 the BOTTOM. A cell "
    "is 1 if filled, 0 if empty. `current` is the falling piece (its absolute "
    "[row,col] cells); `next` is the piece after it.\n\n"
    "Goal: clear full rows. Keep the stack LOW and FLAT and never trap an empty "
    "cell under a filled one (a hole) — holes are permanent and lose the game.\n\n"
    "Plan where the CURRENT piece should land, then output the exact controller "
    "sequence to get it there: zero or more ROTATE, then move horizontally with "
    "LEFT *or* RIGHT (never both), then a single final DROP. Think one piece ahead: "
    "also give your intended plan for the `next` piece. You only commit the current "
    "piece now; you'll re-plan once it locks.\n\n"
    "Be terse: output ONLY the `moves` array and a short `next_intent` (a few words). "
    "No explanations."
)

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "moves": {"type": "array", "items": {"type": "string"}},
        "next_intent": {"type": "string"},
    },
    "required": ["moves"],
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
        self._intent: list[str] | None = None  # "json" mode: last turn's plan for this piece

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

    def _json_user(self, state: GameState, feedback: str | None) -> str:
        board = state.raw.get("board") or []
        grid = [[1 if cell else 0 for cell in row] for row in board]
        if not any(any(row) for row in grid):
            self._intent = None  # fresh board — drop stale one-step-ahead memory
        current = state.raw.get("current", {})
        payload = {
            "cols": len(grid[0]) if grid else 10,
            "rows": len(grid),
            "current": {"type": current.get("type"), "cells": current.get("cells", [])},
            "next": state.raw.get("next"),
            "board": grid,
        }
        stats = (
            f"stats: height={state.raw.get('stack_height')} "
            f"holes={state.raw.get('holes')} lines={state.raw.get('lines')}"
        )
        memory = (
            f"\nLast turn you intended this plan for the now-current piece: "
            f"{self._intent}. Keep it if still good, or revise."
            if self._intent else ""
        )
        return (
            f"{json.dumps(payload)}\n\n{stats}\n"
            f"feedback: {feedback or 'none'}{memory}\n"
            "Output `moves` for the current piece (ROTATEs, then LEFT or RIGHT, then "
            "DROP) and `next_intent` (your plan for the next piece)."
        )

    def _decide_plan(self, state: GameState, feedback: str | None) -> Action:
        client = self._ensure_client()
        content = self._json_user(state, feedback)
        # Pure-LLM run with no recovery worker — a single transient API blip would
        # otherwise end the game. Retry a few times before giving up.
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    system=PLAN_SYSTEM,
                    messages=[{"role": "user", "content": content}],
                    output_config={"format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
                )
                text = next(
                    (b.text for b in resp.content if getattr(b, "type", None) == "text"), None
                )
                if not text:
                    raise ValueError("no text block in response")
                data = json.loads(text)
                self._intent = (data.get("next_intent") or "").strip() or None
                valid = ("LEFT", "RIGHT", "ROTATE", "DOWN", "DROP")
                moves = [b for b in data.get("moves", []) if b in valid]
                return Action(tuple(moves) or ("DROP",), 6)
            except Exception as e:  # transient API/parse error — retry
                last_exc = e
                import time

                time.sleep(0.6 * (attempt + 1))
        raise last_exc  # type: ignore[misc]

    def decide(self, state: GameState, feedback: str | None) -> Action:
        if self.perception == "json":
            return self._decide_plan(state, feedback)
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
