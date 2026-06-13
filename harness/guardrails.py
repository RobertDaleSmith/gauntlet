"""🛡️ Guardrails pillar — declared rules on controller input.

Rules are a literal, inspectable list (not logic buried in the loop). Each rule
returns a Verdict; the harness validates an action *before* it reaches the game.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .types import BUTTONS, Action, GameState


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reason: str | None = None
    guardrail: str | None = None


class Guardrail(Protocol):
    name: str

    def check(self, action: Action, state: GameState) -> Verdict: ...


class AllowedButtons:
    name = "ALLOWED_BUTTONS"

    def check(self, action: Action, state: GameState) -> Verdict:
        bad = [b for b in action.buttons if b not in BUTTONS]
        if bad:
            return Verdict(False, f"unknown buttons: {bad}", self.name)
        return Verdict(True)


class MaxHoldFrames:
    name = "MAX_HOLD_FRAMES"

    def __init__(self, limit: int = 120) -> None:
        self.limit = limit

    def check(self, action: Action, state: GameState) -> Verdict:
        if action.hold_frames > self.limit:
            return Verdict(
                False, f"hold {action.hold_frames} > max {self.limit}", self.name
            )
        return Verdict(True)


class NoImpossibleCombos:
    name = "NO_IMPOSSIBLE_COMBOS"
    OPPOSITES = (("LEFT", "RIGHT"), ("UP", "DOWN"))

    def check(self, action: Action, state: GameState) -> Verdict:
        held = set(action.buttons)
        for a, b in self.OPPOSITES:
            if a in held and b in held:
                return Verdict(False, f"opposing inputs: {a}+{b}", self.name)
        return Verdict(True)


# The declared guardrail set. This is what "guardrails are declared" means.
DEFAULT_GUARDRAILS: list[Guardrail] = [
    AllowedButtons(),
    MaxHoldFrames(120),
    NoImpossibleCombos(),
]


class GuardrailSet:
    """Validates an action against every declared rule; first block wins."""

    def __init__(self, rules: list[Guardrail] | None = None) -> None:
        self.rules = rules if rules is not None else list(DEFAULT_GUARDRAILS)

    def validate(self, action: Action, state: GameState) -> Verdict:
        for rule in self.rules:
            verdict = rule.check(action, state)
            if not verdict.allowed:
                return verdict
        return Verdict(True)
