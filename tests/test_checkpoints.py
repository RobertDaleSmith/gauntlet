from harness.checkpoints import (
    LinesMilestone,
    NoNewHoles,
    NotGameOver,
    StackHeightSafe,
)
from harness.types import GameState


def test_stack_height_safe_pass_and_fail():
    cp = StackHeightSafe(danger=12)
    assert cp.evaluate(GameState(0), GameState(1, stack_height=10)).passed
    assert not cp.evaluate(GameState(0), GameState(1, stack_height=15)).passed


def test_not_game_over():
    assert NotGameOver().evaluate(GameState(0), GameState(1, game_over=False)).passed
    assert not NotGameOver().evaluate(GameState(0), GameState(1, game_over=True)).passed


def test_no_new_holes():
    a = GameState(0, holes=2)
    assert NoNewHoles().evaluate(a, GameState(1, holes=2)).passed
    assert not NoNewHoles().evaluate(a, GameState(1, holes=4)).passed


def test_lines_milestone_gate():
    cp = LinesMilestone(4)
    assert cp.evaluate(GameState(0), GameState(1, lines=4)).passed
    assert not cp.evaluate(GameState(0), GameState(1, lines=2)).passed
