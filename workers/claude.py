"""Claude worker (Anthropic SDK, Haiku 4.5, structured-output actions).

STUB — to be built. Reads structured GameState, returns an Action via a forced
tool / structured output. Keep thinking off for latency; Haiku is the reflex
layer. Model id: claude-haiku-4-5.

See docs/ and ARCHITECTURE.md. Until built, importing this should not crash the
harness — the scripted worker is the default.
"""
from __future__ import annotations

from harness.types import Action, GameState

MODEL = "claude-haiku-4-5"


class ClaudeWorker:
    name = "claude"

    def __init__(self, model: str = MODEL) -> None:
        self.model = model
        # TODO(ralph): construct anthropic.Anthropic() client here.

    def decide(self, state: GameState, feedback: str | None) -> Action:
        # TODO(ralph): call Claude with structured output -> {buttons, hold_frames}.
        # Prompt: current GameState + optional feedback hint; force a typed action.
        raise NotImplementedError("ClaudeWorker.decide is not built yet")
