"""A deliberately limited worker, built to demonstrate *recoverable* failure.

It places pieces competently (minimizes holes/bumpiness) but confines itself to
the left part of the board, never touching the rightmost `GAP_COLS` columns. With
a whole column always empty, no row can ever complete — so it never clears a line
and the stack just climbs. Crucially its failure mode is pure **height**, not
buried holes: the board stays clean. That lets a full-board recovery worker swap
in, fill the abandoned columns, clear the backlog, and visibly dig the stack back
down — a real, observable recovery (unlike the reckless worker, whose holes are
permanent and unrecoverable).
"""
from __future__ import annotations

from harness.types import Action, GameState
from workers.heuristic import _drop_y, _norm, _result, _rotations, _score

# How many right-hand columns the sloppy agent refuses to use.
GAP_COLS = 3


class SloppyWorker:
    name = "sloppy"

    def decide(self, state: GameState, feedback: str | None) -> Action:
        board = state.raw.get("board")
        current = state.raw.get("current")
        if not board or not current:
            return Action(("DROP",), 4)

        rows, cols = len(board), len(board[0])
        usable = max(1, cols - GAP_COLS)  # never place into the rightmost GAP_COLS
        cur_cells = [tuple(c) for c in current["cells"]]
        cur_shape = _norm(cur_cells)
        cur_x = min(c for _, c in cur_cells)
        variants = _rotations(cur_shape)

        best = None  # (score, shape, ox)
        for shape in variants:
            maxc = max(c for _, c in shape)
            for ox in range(0, usable - maxc):
                oy = _drop_y(board, shape, ox, rows, cols)
                if oy is None:
                    continue
                b, cleared = _result(board, shape, oy, ox, rows, cols)
                s = _score(b, cleared, rows, cols)
                if best is None or s > best[0]:
                    best = (s, shape, ox)

        if best is None:
            return Action(("DROP",), 4)

        _, target_shape, target_x = best
        if cur_shape != target_shape:
            return Action(("ROTATE",), 4)
        if cur_x < target_x:
            return Action(("RIGHT",), 4)
        if cur_x > target_x:
            return Action(("LEFT",), 4)
        return Action(("DROP",), 4)
