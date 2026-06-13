"""Shared types passed between the harness and the worker."""
from __future__ import annotations

from dataclasses import dataclass, field

# Valid NES controller buttons. Guardrails reference this set.
BUTTONS = frozenset({"LEFT", "RIGHT", "UP", "DOWN", "A", "B", "START", "SELECT"})


@dataclass(frozen=True)
class GameState:
    """Normalized game state the agent reasons over (read from emulator RAM)."""

    frame: int
    x: int = 0
    score: int = 0
    lives: int = 3
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """An intent the worker proposes: hold these buttons for N frames."""

    buttons: tuple[str, ...]
    hold_frames: int = 30
