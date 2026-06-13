from harness.types import BUTTONS, GameState
from workers.heuristic import HeuristicWorker


def _empty_board(rows=20, cols=10):
    return [[0] * cols for _ in range(rows)]


def _state(board, cells):
    return GameState(0, raw={"board": board, "current": {"type": "T", "cells": cells}})


def test_returns_legal_action_on_empty_board():
    # O piece spawned near the left.
    s = _state(_empty_board(), [[0, 0], [0, 1], [1, 0], [1, 1]])
    a = HeuristicWorker().decide(s, None)
    assert all(b in BUTTONS for b in a.buttons)


def test_fail_safe_without_board():
    a = HeuristicWorker().decide(GameState(0), None)
    assert a.buttons == ("DROP",)


def test_moves_toward_a_flat_landing():
    # Build a board where columns 0-8 are filled high and column 9 is open;
    # the worker should move RIGHT toward the open column rather than stack left.
    board = _empty_board()
    for r in range(15, 20):
        for c in range(0, 9):
            board[r][c] = 1
    # vertical I-ish piece on the far left
    s = _state(board, [[0, 0], [1, 0], [2, 0], [3, 0]])
    a = HeuristicWorker().decide(s, None)
    assert a.buttons[0] in ("RIGHT", "ROTATE")  # not stacking further left


def test_lookahead_runs_with_next_piece():
    board = _empty_board()
    s = GameState(0, raw={"board": board,
                          "current": {"type": "T", "cells": [[0, 1], [1, 0], [1, 1], [1, 2]]},
                          "next": "I"})
    a = HeuristicWorker().decide(s, None)
    assert all(b in BUTTONS for b in a.buttons)


def test_unknown_next_falls_back_to_one_ply():
    board = _empty_board()
    s = GameState(0, raw={"board": board,
                          "current": {"type": "O", "cells": [[0, 0], [0, 1], [1, 0], [1, 1]]},
                          "next": "?"})
    a = HeuristicWorker().decide(s, None)
    assert all(b in BUTTONS for b in a.buttons)
