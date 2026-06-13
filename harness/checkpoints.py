"""✅ Checkpoints pillar — explicit pass/fail evaluation of progress.

Each checkpoint reads game state (objective, from RAM — no fuzzy judging) and
returns a pass/fail result. Results are persisted by the material handler.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .types import GameState


@dataclass(frozen=True)
class CheckpointResult:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


class Checkpoint(Protocol):
    name: str

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult: ...


class ForwardProgress:
    name = "FORWARD_PROGRESS"

    def __init__(self, min_delta: int = 5) -> None:
        self.min_delta = min_delta

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        delta = new.x - prev.x
        return CheckpointResult(
            self.name, delta >= self.min_delta, f"x {prev.x}->{new.x} (Δ{delta})"
        )


class StillAlive:
    name = "STILL_ALIVE"

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(
            self.name, new.lives >= prev.lives, f"lives {prev.lives}->{new.lives}"
        )


class ScoreNonDecreasing:
    name = "SCORE_NON_DECREASING"

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(
            self.name, new.score >= prev.score, f"score {prev.score}->{new.score}"
        )


class LevelAdvanced:
    name = "LEVEL_ADVANCED"

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(
            self.name, new.level >= prev.level, f"level {prev.level}->{new.level}"
        )


class ScoreMilestone:
    """Gate checkpoint — passes once score reaches a threshold (not a default)."""

    name = "SCORE_MILESTONE"

    def __init__(self, threshold: int) -> None:
        self.threshold = threshold

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(
            self.name, new.score >= self.threshold, f"score {new.score} / {self.threshold}"
        )


DEFAULT_CHECKPOINTS: list[Checkpoint] = [
    ForwardProgress(),
    StillAlive(),
    ScoreNonDecreasing(),
    LevelAdvanced(),
]
