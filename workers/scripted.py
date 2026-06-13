"""A rule-based Tetris worker. No LLM — fast iteration + the live-swap demo bonus.

Default: drop pieces straight down (reckless — the stack climbs). When the
harness feeds back that the stack is too high, place deliberately (reposition,
then drop) to clear lines. This minimal agent exercises the feedback loop.
"""
from __future__ import annotations

from harness.types import Action, GameState


class ScriptedWorker:
    name = "scripted"

    def decide(self, state: GameState, feedback: str | None) -> Action:
        if feedback and ("height" in feedback.lower() or "stack" in feedback.lower()):
            return Action(("LEFT", "DROP"), 4)  # deliberate placement -> clears
        return Action(("DROP",), 4)  # reckless straight drop
