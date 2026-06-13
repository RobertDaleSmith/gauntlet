"""Game adapters. FakeGameAdapter simulates Mario for tests + offline dev;
WebSocketGameAdapter drives a real in-browser game over a transport.

The harness only depends on the GameAdapter protocol, so any adapter drops in
unchanged.
"""
from __future__ import annotations

from typing import Protocol

from .types import Action, GameState


class FakeTetrisAdapter:
    """Tetris sim for tests/offline dev — no browser needed.

    Encodes the hero beat: a reckless DROP raises the stack; once the harness
    feeds back that the stack is too high, a thoughtful placement (repositioning
    with LEFT/RIGHT before dropping) clears a line and lowers it. Tops out at 20.
    """

    DANGER = 12
    TOP_OUT = 20

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._frame = 0
        self._height = 0
        self._lines = 0
        self._score = 0
        self._holes = 0
        self._over = False

    def _raw(self) -> dict:
        return {
            "frame": self._frame,
            "stack_height": self._height,
            "lines": self._lines,
            "score": self._score,
            "holes": self._holes,
            "game_over": self._over,
            "level": 1,
        }

    def read_state(self) -> dict:
        return self._raw()

    def execute(self, action: Action, state: GameState) -> dict:
        self._frame += action.hold_frames
        held = set(action.buttons)
        thoughtful = ("LEFT" in held or "RIGHT" in held) and self._height > 0
        if thoughtful:  # placed deliberately -> clears a line
            self._height = max(0, self._height - 3)
            self._lines += 1
            self._score += 100
        else:  # reckless drop -> stack climbs
            self._height += 2
        if self._height >= self.TOP_OUT:
            self._over = True
        return self._raw()


# Back-compat alias (the protocol is the same).
FakeGameAdapter = FakeTetrisAdapter


class Transport(Protocol):
    """Request/response channel to the browser (a WebSocket in production)."""

    def request(self, message: dict) -> dict: ...


class WebSocketGameAdapter:
    """GameAdapter backed by a Transport. Sends typed messages, gets state back.

    The browser runs jsnes and answers these messages; the harness is unaware of
    the wire details. Implements the same protocol as FakeGameAdapter, so it is a
    drop-in replacement with no harness changes.
    """

    def __init__(self, transport: Transport) -> None:
        self.transport = transport

    def read_state(self) -> dict:
        return self.transport.request({"type": "read_state"})

    def execute(self, action: Action, state: GameState) -> dict:
        return self.transport.request(
            {
                "type": "execute",
                "buttons": list(action.buttons),
                "hold_frames": action.hold_frames,
            }
        )

    def reset(self) -> dict:
        return self.transport.request({"type": "reset"})


class NullAdapter:
    """No-op adapter for when an external executor (the browser) drives the game.

    The harness uses loop.decide()/observe() directly; execute() is never called.
    """

    def read_state(self) -> dict:
        return {}

    def execute(self, action: Action, state: GameState) -> dict:
        return {}

    def reset(self) -> None:
        pass
