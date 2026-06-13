"""Game adapters. FakeGameAdapter simulates Mario for tests + offline dev.

The real adapter (jsnes over WebSocket) is built later; the harness only depends
on the GameAdapter protocol, so any adapter drops in unchanged.
"""
from __future__ import annotations

from .types import Action, GameState


class FakeGameAdapter:
    """Mario-ish sim: advances on RIGHT, stuck at a pipe until JUMP (A).

    Encodes the demo's hero beat so the feedback loop is testable without an
    emulator: stuck -> hint -> adapt (press A) -> clears the pipe.
    """

    PIPE_X = 400

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._frame = 0
        self._x = 380
        self._score = 0
        self._lives = 3

    def _raw(self) -> dict:
        return {
            "frame": self._frame,
            "x": self._x,
            "score": self._score,
            "lives": self._lives,
        }

    def read_state(self) -> dict:
        return self._raw()

    def execute(self, action: Action, state: GameState) -> dict:
        self._frame += action.hold_frames
        held = set(action.buttons)
        at_pipe = self.PIPE_X - 10 <= self._x <= self.PIPE_X + 10
        if at_pipe:
            if "A" in held:  # jump clears the pipe
                self._x += 60
                self._score += 100
            # RIGHT alone at the pipe: no progress (stuck)
        elif "RIGHT" in held:
            self._x += 7
        return self._raw()
