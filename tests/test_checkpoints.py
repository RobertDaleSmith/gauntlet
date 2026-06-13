from harness.checkpoints import (
    ForwardProgress,
    LevelAdvanced,
    ScoreMilestone,
    ScoreNonDecreasing,
    StillAlive,
)
from harness.types import GameState


def test_forward_progress_pass_and_fail():
    a, b = GameState(0, x=100), GameState(1, x=110)
    assert ForwardProgress(min_delta=5).evaluate(a, b).passed
    assert not ForwardProgress(min_delta=5).evaluate(a, GameState(1, x=102)).passed


def test_still_alive_fails_on_life_loss():
    a, b = GameState(0, lives=3), GameState(1, lives=2)
    assert not StillAlive().evaluate(a, b).passed


def test_score_non_decreasing():
    a = GameState(0, score=100)
    assert ScoreNonDecreasing().evaluate(a, GameState(1, score=100)).passed
    assert not ScoreNonDecreasing().evaluate(a, GameState(1, score=50)).passed


def test_level_advanced():
    a = GameState(0, level=1)
    assert LevelAdvanced().evaluate(a, GameState(1, level=2)).passed
    assert not LevelAdvanced().evaluate(a, GameState(1, level=0)).passed


def test_score_milestone_gate():
    cp = ScoreMilestone(1000)
    assert cp.evaluate(GameState(0), GameState(1, score=1000)).passed
    assert not cp.evaluate(GameState(0), GameState(1, score=500)).passed
