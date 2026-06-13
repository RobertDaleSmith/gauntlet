"""Claude worker — Anthropic SDK, Haiku 4.5, structured-output actions.

Reads structured GameState, returns an Action via structured output
(`{buttons, hold_frames}`). Haiku is the fast reflex layer, so thinking is left
off for latency. The client is injectable for testing; in production it lazily
constructs `anthropic.Anthropic()`.
"""
from __future__ import annotations

import json

from harness.types import Action, GameState

MODEL = "claude-haiku-4-5"

SYSTEM = (
    "You play NES games through a controller. Given the current game state, "
    "return the next action: which buttons to hold and for how many frames. "
    "Move RIGHT to make forward progress; press A to jump over obstacles. "
    "If feedback says you are stuck, change your approach (e.g. add a jump)."
)

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "buttons": {"type": "array", "items": {"type": "string"}},
        "hold_frames": {"type": "integer"},
    },
    "required": ["buttons", "hold_frames"],
    "additionalProperties": False,
}


class ClaudeWorker:
    name = "claude"

    def __init__(self, client=None, model: str = MODEL) -> None:
        self.client = client
        self.model = model

    def _ensure_client(self):
        if self.client is None:
            import anthropic  # lazy: package only needed when actually running

            self.client = anthropic.Anthropic()
        return self.client

    def _prompt(self, state: GameState, feedback: str | None) -> str:
        return (
            f"state: x={state.x} score={state.score} lives={state.lives} "
            f"level={state.level} frame={state.frame}\n"
            f"feedback: {feedback or 'none'}\n"
            "Return the next action."
        )

    def decide(self, state: GameState, feedback: str | None) -> Action:
        resp = self._ensure_client().messages.create(
            model=self.model,
            max_tokens=256,
            system=SYSTEM,
            messages=[{"role": "user", "content": self._prompt(state, feedback)}],
            output_config={"format": {"type": "json_schema", "schema": ACTION_SCHEMA}},
        )
        text = next(b.text for b in resp.content if getattr(b, "type", None) == "text")
        data = json.loads(text)
        return Action(tuple(data["buttons"]), int(data["hold_frames"]))
