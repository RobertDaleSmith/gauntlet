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
# Pure-planner experiment: no local candidate enumeration or move scoring. From a
# SINGLE snapshot the model plans BOTH the current and next piece — the way a human
# reads the board once and knows the buttons for both. It gets a `plan` field to
# reason in (simulate gravity/rotations, find completing rows) before committing,
# with a generous token budget so the JSON never truncates. We execute the current
# piece, cache the next-piece moves (the game is deterministic, so a self-consistent
# 2-piece plan stays valid), then re-snapshot for the third piece.
PLAN_SYSTEM = (
    "You are playing Tetris by driving a controller. The board is a JSON grid, "
    "10 columns wide and 20 rows tall; row 0 is the TOP, row 19 the BOTTOM. A cell "
    "is 1 if filled, 0 if empty. `current` is the falling piece (its absolute "
    "[row,col] cells); `next` is the piece after it.\n\n"
    "You get ONE snapshot and must plan BOTH pieces — a skilled human reads the "
    "board once and immediately knows the buttons for both. Do the same.\n\n"
    "Think it through in `plan`: for the CURRENT piece pick a target column and "
    "rotation, mentally drop it (it falls until it hits something) and check it "
    "creates no hole and ideally completes a row; then, assuming it landed there, "
    "plan the NEXT piece the same way. Keep the stack LOW and FLAT and NEVER trap "
    "an empty cell under a filled one.\n\n"
    "`rows_by_fill` lists the most-filled rows and the exact columns each is still "
    "missing. A row CLEARS only when all 10 columns are filled. Your TOP priority is "
    "to COMPLETE the most-filled row by dropping pieces into its missing columns — "
    "finish bottom rows fully before spreading pieces out. Clearing rows is how you "
    "win; a tidy board that never completes a row will still lose.\n\n"
    "Then output `current_moves` and `next_moves`. Each list: zero or more ROTATE, "
    "then move with LEFT or RIGHT (never both in one list), then a single final DROP."
)

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "plan": {"type": "string"},
        "current_moves": {"type": "array", "items": {"type": "string"}},
        "next_moves": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["current_moves"],
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
        self._pending: list[str] | None = None  # "json" mode: cached next-piece moves

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

    _VALID = ("LEFT", "RIGHT", "ROTATE", "DOWN", "DROP")

    def _json_user(self, state: GameState, feedback: str | None) -> str:
        board = state.raw.get("board") or []
        grid = [[1 if cell else 0 for cell in row] for row in board]
        current = state.raw.get("current", {})
        # Per-row fill hint: surface the near-complete rows and their exact gaps so
        # the model can target line completion (its missing skill), not just tidiness.
        cur_cells = {tuple(c) for c in current.get("cells", [])}
        rows_by_fill = []
        for r, row in enumerate(grid):
            missing = [c for c, v in enumerate(row) if not v and (r, c) not in cur_cells]
            filled = len(row) - len(missing)
            if filled:
                rows_by_fill.append({"row": r, "filled": filled, "missing": missing})
        rows_by_fill.sort(key=lambda x: -x["filled"])
        payload = {
            "cols": len(grid[0]) if grid else 10,
            "rows": len(grid),
            "current": {"type": current.get("type"), "cells": current.get("cells", [])},
            "next": state.raw.get("next"),
            "rows_by_fill": rows_by_fill[:6],
            "board": grid,
        }
        stats = (
            f"stats: height={state.raw.get('stack_height')} "
            f"holes={state.raw.get('holes')} lines={state.raw.get('lines')}"
        )
        return (
            f"{json.dumps(payload)}\n\n{stats}\n"
            f"feedback: {feedback or 'none'}\n"
            "Reason in `plan`, then output `current_moves` and `next_moves` "
            "(each: ROTATEs, then LEFT or RIGHT, then DROP)."
        )

    def _decide_plan(self, state: GameState, feedback: str | None) -> Action:
        board = state.raw.get("board") or []
        if not any(any(cell for cell in row) for row in board):
            self._pending = None  # fresh board — drop a stale cached plan

        # Second piece of a 2-piece plan: execute the cached moves, no API call.
        if self._pending is not None:
            moves = [b for b in self._pending if b in self._VALID]
            self._pending = None
            return Action(tuple(moves) or ("DROP",), 6)

        client = self._ensure_client()
        content = self._json_user(state, feedback)
        # Pure-LLM run with no recovery worker — a single transient API blip would
        # otherwise end the game. Retry a few times before giving up.
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = client.messages.create(
                    model=self.model,
                    max_tokens=1500,  # room to reason in `plan` without truncating JSON
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
                cur = [b for b in data.get("current_moves", []) if b in self._VALID]
                nxt = [b for b in data.get("next_moves", []) if b in self._VALID]
                self._pending = nxt or None  # cache the next piece's moves
                return Action(tuple(cur) or ("DROP",), 6)
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
