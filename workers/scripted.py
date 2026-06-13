"""A rule-based worker. No LLM — fast iteration + the live-swap demo bonus.

Default: walk right. When the harness feeds back a "stuck / try jump" hint,
add the A button. This is the minimal agent that exercises the feedback loop.
"""
from __future__ import annotations

from harness.types import Action, GameState


class ScriptedWorker:
    name = "scripted"

    def decide(self, state: GameState, feedback: str | None) -> Action:
        if feedback and ("jump" in feedback.lower() or "stuck" in feedback.lower()):
            return Action(("RIGHT", "A"), 30)
        return Action(("RIGHT",), 30)
