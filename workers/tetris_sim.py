"""Local placement enumerator — the geometry the LLM is bad at, done in code.

Mirrors the browser game's exact input semantics (server/static/tetris.js): CW
rotation with wall-kick offsets [0,-1,1,-2,2], single-step LEFT/RIGHT, hard DROP.
For a given board + current piece it returns every distinct legal final placement
with (a) the exact button sequence that produces it and (b) the consequences
(lines cleared, holes, max height, bumpiness). The candidate-select worker hands
these to the LLM so it only has to *judge*, never compute geometry or move counts.
"""
from __future__ import annotations

Cells = tuple  # tuple[tuple[int, int], ...]


def _collide(board, rel, x, y, rows, cols) -> bool:
    for r, c in rel:
        R, C = y + r, x + c
        if C < 0 or C >= cols or R >= rows:
            return True
        if R >= 0 and board[R][C]:
            return True
    return False


def _rotate(rel):
    # CW: (r,c) -> (c,-r), then normalize to non-negative (matches tetris.js).
    rot = [(c, -r) for r, c in rel]
    minr = min(r for r, _ in rot)
    minc = min(c for _, c in rot)
    return tuple(sorted((r - minr, c - minc) for r, c in rot))


def _try_rotate(board, rel, x, y, rows, cols):
    rc = _rotate(rel)
    for dx in (0, -1, 1, -2, 2):  # wall kicks, in the game's order
        if not _collide(board, rc, x + dx, y, rows, cols):
            return rc, x + dx
    return None, x


def _features(board, cells, rows, cols) -> dict:
    b = [row[:] for row in board]
    for r, c in cells:
        b[r][c] = 1
    full = {r for r in range(rows) if all(b[r])}
    lines = len(full)
    if lines:
        b = [row for r, row in enumerate(b) if r not in full]
        while len(b) < rows:
            b.insert(0, [0] * cols)
    heights = [0] * cols
    holes = 0
    for c in range(cols):
        seen = False
        for r in range(rows):
            if b[r][c]:
                if not seen:
                    heights[c] = rows - r
                    seen = True
            elif seen:
                holes += 1
    maxh = max(heights) if heights else 0
    bump = sum(abs(heights[i] - heights[i + 1]) for i in range(cols - 1))
    return {"lines": lines, "holes": holes, "max_h": maxh, "bumpiness": bump}


def enumerate_placements(board, cur_abs) -> list[dict]:
    """All distinct legal placements for the current piece, each with its exact
    button sequence (ROTATEs, then LEFT/RIGHT, then DROP) and consequences."""
    rows, cols = len(board), len(board[0])
    y0 = min(r for r, _ in cur_abs)
    x0 = min(c for _, c in cur_abs)
    rel0 = tuple(sorted((r - y0, c - x0) for r, c in cur_abs))

    out: list[dict] = []
    seen: set = set()
    for r in range(4):
        rel, x = rel0, x0
        rot_moves: list[str] = []
        blocked = False
        for _ in range(r):
            rc, nx = _try_rotate(board, rel, x, y0, rows, cols)
            if rc is None:
                blocked = True
                break
            rel, x = rc, nx
            rot_moves.append("ROTATE")
        if blocked:
            continue
        for direction, key in ((-1, "LEFT"), (1, "RIGHT")):
            cx, steps = x, 0
            while True:
                dy = y0
                while not _collide(board, rel, cx, dy + 1, rows, cols):
                    dy += 1
                cells = tuple(sorted((dy + rr, cx + cc) for rr, cc in rel))
                if all(rr >= 0 for rr, _ in cells) and cells not in seen:
                    seen.add(cells)
                    moves = rot_moves + [key] * steps + ["DROP"]
                    occ = sorted({cc for _, cc in cells})
                    out.append({
                        "moves": moves, "col": occ[0], "cols": occ,
                        **_features(board, cells, rows, cols),
                    })
                if _collide(board, rel, cx + direction, y0, rows, cols):
                    break
                cx += direction
                steps += 1
    return out
