"""A competent rule-based Tetris worker (no LLM, no vision).

Reads the ground-truth board from state.raw and picks the placement that
minimizes height/holes/bumpiness and maximizes line clears (El-Tetris weights).
Uses one-piece **lookahead** (the `next` piece) when available — a 2-ply search —
then emits one controller input per step toward the chosen placement. Re-plans
each step against the live board, so it's robust to rotation wall-kicks.

This is a *baseline* — it's allowed to read structured state. The vision goal
(see pixels, play like a human) is the ClaudeWorker's job.
"""
from __future__ import annotations

from harness.types import Action, GameState

# El-Tetris weights.
W_AGG, W_LINES, W_HOLES, W_BUMP = -0.510066, 0.760666, -0.35663, -0.184483

# Base spawn shapes by piece type (match server/static/tetris.js).
PIECE_CELLS = {
    "I": [[0, 0], [0, 1], [0, 2], [0, 3]],
    "O": [[0, 0], [0, 1], [1, 0], [1, 1]],
    "T": [[0, 1], [1, 0], [1, 1], [1, 2]],
    "S": [[0, 1], [0, 2], [1, 0], [1, 1]],
    "Z": [[0, 0], [0, 1], [1, 1], [1, 2]],
    "J": [[0, 0], [1, 0], [1, 1], [1, 2]],
    "L": [[0, 2], [1, 0], [1, 1], [1, 2]],
}


def _norm(cells):
    minr = min(r for r, _ in cells)
    minc = min(c for _, c in cells)
    return frozenset((r - minr, c - minc) for r, c in cells)


def _rot(shape):
    return _norm([(c, -r) for r, c in shape])


def _rotations(shape):
    out, s = [], shape
    for _ in range(4):
        if s not in out:
            out.append(s)
        s = _rot(s)
    return out


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


def _result(board, shape, oy, ox, rows, cols):
    """Place the piece, clear full rows; return (new_board, lines_cleared)."""
    placed = [row[:] for row in board]
    for r, c in shape:
        if oy + r >= 0:
            placed[oy + r][ox + c] = 1
    kept = [row for row in placed if not all(row)]
    cleared = rows - len(kept)
    while len(kept) < rows:
        kept.insert(0, [0] * cols)
    return kept, cleared


def _score(board, cleared, rows, cols):
    heights = [0] * cols
    holes = 0
    for c in range(cols):
        seen = False
        for r in range(rows):
            if board[r][c]:
                if not seen:
                    heights[c] = rows - r
                    seen = True
            elif seen:
                holes += 1
    agg = sum(heights)
    bump = sum(abs(heights[i] - heights[i + 1]) for i in range(cols - 1))
    return W_AGG * agg + W_LINES * cleared + W_HOLES * holes + W_BUMP * bump


def _best_score(board, variants, rows, cols):
    """Best placement score for a piece (given its rotation variants) on a board."""
    best = None
    for shape in variants:
        maxc = max(c for _, c in shape)
        for ox in range(0, cols - maxc):
            oy = _drop_y(board, shape, ox, rows, cols)
            if oy is None:
                continue
            b, cleared = _result(board, shape, oy, ox, rows, cols)
            s = _score(b, cleared, rows, cols)
            if best is None or s > best:
                best = s
    return best if best is not None else 0.0


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
        variants = _rotations(cur_shape)

        # Lookahead: the next piece's best response, if we know what it is.
        next_type = state.raw.get("next")
        next_variants = (
            _rotations(_norm([tuple(c) for c in PIECE_CELLS[next_type]]))
            if next_type in PIECE_CELLS
            else None
        )

        best = None  # (total_score, target_shape, ox)
        for shape in variants:
            maxc = max(c for _, c in shape)
            for ox in range(0, cols - maxc):
                oy = _drop_y(board, shape, ox, rows, cols)
                if oy is None:
                    continue
                b1, cleared = _result(board, shape, oy, ox, rows, cols)
                total = _score(b1, cleared, rows, cols)
                if next_variants is not None:
                    total += _best_score(b1, next_variants, rows, cols)
                if best is None or total > best[0]:
                    best = (total, shape, ox)

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
