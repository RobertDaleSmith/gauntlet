"""A competent rule-based Tetris worker (no LLM, no vision).

Reads the ground-truth board from state.raw and picks the placement that
minimizes height/holes/bumpiness and maximizes line clears (El-Tetris weights),
then emits one controller input per step toward that placement. Re-plans each
step against the live board, so it's robust to rotation wall-kicks.

This is a *baseline* — it's allowed to read structured state. The vision goal
(see pixels, play like a human) is the ClaudeWorker's job.
"""
from __future__ import annotations

from harness.types import Action, GameState

# El-Tetris weights.
W_AGG, W_LINES, W_HOLES, W_BUMP = -0.510066, 0.760666, -0.35663, -0.184483


def _norm(cells):
    minr = min(r for r, _ in cells)
    minc = min(c for _, c in cells)
    return frozenset((r - minr, c - minc) for r, c in cells)


def _rot(shape):
    return _norm([(c, -r) for r, c in shape])


def _collides(board, shape, oy, ox, rows, cols):
    for r, c in shape:
        R, C = oy + r, ox + c
        if C < 0 or C >= cols or R >= rows:
            return True
        if R >= 0 and board[R][C]:
            return True
    return False


def _drop_y(board, shape, ox, rows, cols):
    if _collides(board, shape, -2, ox, rows, cols):
        return None  # invalid x
    oy = -2
    while not _collides(board, shape, oy + 1, ox, rows, cols):
        oy += 1
    return oy


def _evaluate(board, shape, oy, ox, rows, cols):
    placed = [row[:] for row in board]
    for r, c in shape:
        if oy + r >= 0:
            placed[oy + r][ox + c] = 1
    kept = [row for row in placed if not all(row)]
    cleared = rows - len(kept)
    while len(kept) < rows:
        kept.insert(0, [0] * cols)
    heights = [0] * cols
    holes = 0
    for c in range(cols):
        seen = False
        for r in range(rows):
            if kept[r][c]:
                if not seen:
                    heights[c] = rows - r
                    seen = True
            elif seen:
                holes += 1
    agg = sum(heights)
    bump = sum(abs(heights[i] - heights[i + 1]) for i in range(cols - 1))
    return W_AGG * agg + W_LINES * cleared + W_HOLES * holes + W_BUMP * bump


class HeuristicWorker:
    name = "heuristic"

    def decide(self, state: GameState, feedback: str | None) -> Action:
        board = state.raw.get("board")
        current = state.raw.get("current")
        if not board or not current:
            return Action(("DROP",), 4)  # no board info — fail safe

        rows, cols = len(board), len(board[0])
        cur_cells = [tuple(c) for c in current["cells"]]
        cur_shape = _norm(cur_cells)
        cur_x = min(c for _, c in cur_cells)

        # Enumerate distinct rotations of the current piece.
        shapes, s = [], cur_shape
        for _ in range(4):
            if s not in shapes:
                shapes.append(s)
            s = _rot(s)

        best = None  # (score, target_shape, ox)
        for shape in shapes:
            maxc = max(c for _, c in shape)
            for ox in range(0, cols - maxc):
                oy = _drop_y(board, shape, ox, rows, cols)
                if oy is None:
                    continue
                score = _evaluate(board, shape, oy, ox, rows, cols)
                if best is None or score > best[0]:
                    best = (score, shape, ox)

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
