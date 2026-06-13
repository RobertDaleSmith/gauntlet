"""The worker contract."""
from __future__ import annotations

from typing import Protocol

from harness.types import Action, GameState


class Worker(Protocol):
    name: str

    def decide(self, state: GameState, feedback: str | None) -> Action: ...
