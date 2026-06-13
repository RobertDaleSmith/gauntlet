"""✅ Checkpoints pillar — explicit pass/fail evaluation of progress.

Each checkpoint reads ground-truth game state (objective — no fuzzy judging) and
returns a pass/fail result. Results are persisted by the material handler.

These are the Tetris checkpoints; swap them out and the same harness governs a
different game.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .alarms import Severity
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


class StackHeightSafe:
    """Primary danger checkpoint — fails when the stack climbs too high."""

    name = "STACK_HEIGHT_SAFE"
    severity = Severity.HIGH

    def __init__(self, danger: int = 12) -> None:
        self.danger = danger

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(
            self.name,
            new.stack_height <= self.danger,
            f"height {new.stack_height} (danger {self.danger})",
        )


class NotGameOver:
    name = "NOT_GAME_OVER"
    severity = Severity.HIGH

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(self.name, not new.game_over, f"game_over={new.game_over}")


class NoNewHoles:
    name = "NO_NEW_HOLES"
    severity = Severity.LOW

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(
            self.name, new.holes <= prev.holes, f"holes {prev.holes}->{new.holes}"
        )


class LinesMilestone:
    """Gate checkpoint — passes once cleared lines reach a threshold (not default)."""

    name = "LINES_MILESTONE"
    severity = Severity.LOW

    def __init__(self, threshold: int) -> None:
        self.threshold = threshold

    def evaluate(self, prev: GameState, new: GameState) -> CheckpointResult:
        return CheckpointResult(
            self.name, new.lines >= self.threshold, f"lines {new.lines} / {self.threshold}"
        )


# Primary checkpoint first — the loop escalates on the first one by default.
DEFAULT_CHECKPOINTS: list[Checkpoint] = [
    StackHeightSafe(danger=12),
    NotGameOver(),
    NoNewHoles(),
]
