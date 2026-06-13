"""Shared types passed between the harness and the worker."""
from __future__ import annotations

from dataclasses import dataclass, field

# The controller's logical buttons (match the JS game's input names).
BUTTONS = frozenset({"LEFT", "RIGHT", "ROTATE", "DOWN", "DROP"})


@dataclass(frozen=True)
class GameState:
    """Ground-truth game state the harness referee reads to grade.

    The agent never sees this — it perceives the rendered frame (pixels). These
    fields are what the checkpoints/alarms are computed from.
    """

    frame: int
    score: int = 0
    lines: int = 0
    level: int = 1
    stack_height: int = 0
    holes: int = 0
    game_over: bool = False
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """A controller input the worker proposes: hold these buttons for N frames."""

    buttons: tuple[str, ...]
    hold_frames: int = 4
