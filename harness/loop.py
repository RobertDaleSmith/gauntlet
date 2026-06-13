"""The control loop that ties the four pillars around a swappable worker.

read state -> worker.decide -> guardrails validate -> execute window
  -> checkpoint pass/fail -> on FAIL: feedback hint + alarm -> loop

The agent's behavior changes from feedback: a failed checkpoint injects a hint
into the next decision, and the (same) worker adapts. Repeated failure escalates
to a human STOP.
"""
from __future__ import annotations

import uuid
from typing import Protocol

from .alarms import Alarm, AlarmBus, Severity
from .checkpoints import DEFAULT_CHECKPOINTS, Checkpoint, CheckpointResult
from .guardrails import GuardrailSet
from .material import MaterialHandler
from .types import Action, GameState


class GameAdapter(Protocol):
    """Pluggable game backend (jsnes over WebSocket, a real emulator, etc.)."""

    def read_state(self) -> dict: ...

    def execute(self, action: Action, state: GameState) -> dict: ...

    def reset(self) -> None: ...


class Worker(Protocol):
    def decide(self, state: GameState, feedback: str | None) -> Action: ...


class HarnessLoop:
    def __init__(
        self,
        adapter: GameAdapter,
        worker: Worker,
        guardrails: GuardrailSet | None = None,
        checkpoints: list[Checkpoint] | None = None,
        material: MaterialHandler | None = None,
        alarms: AlarmBus | None = None,
        max_guardrail_retries: int = 3,
        escalate_after: int = 3,
        run_id: str | None = None,
    ) -> None:
        self.adapter = adapter
        self.worker = worker
        self.guardrails = guardrails or GuardrailSet()
        self.checkpoints = checkpoints or list(DEFAULT_CHECKPOINTS)
        self.material = material or MaterialHandler()
        self.alarms = alarms or AlarmBus()
        self.max_guardrail_retries = max_guardrail_retries
        self.escalate_after = escalate_after
        self.run_id = run_id or uuid.uuid4().hex

        self.status = "RUNNING"  # RUNNING | STOP
        self.state = self.material.normalize(self.adapter.read_state())
        self._feedback: str | None = None
        self._consecutive_fails = 0

    def step(self) -> list[CheckpointResult]:
        if self.status != "RUNNING":
            return []

        prev = self.state
        feedback = self._feedback

        # Guardrails: validate the proposed action before it reaches the game.
        action: Action | None = None
        for _ in range(self.max_guardrail_retries):
            candidate = self.worker.decide(prev, feedback)
            verdict = self.guardrails.validate(candidate, prev)
            if verdict.allowed:
                action = candidate
                break
            self.alarms.emit(
                Alarm(
                    "GUARDRAIL_BLOCKED",
                    Severity.HIGH,
                    {"reason": verdict.reason, "guardrail": verdict.guardrail},
                    "revise the action and retry",
                )
            )
            feedback = f"action blocked by {verdict.guardrail}: {verdict.reason}"
        if action is None:
            self.alarms.emit(
                Alarm(
                    "GUARDRAIL_DEADLOCK",
                    Severity.CRITICAL,
                    {"retries": self.max_guardrail_retries},
                    "stop and request human intervention",
                )
            )
            self.status = "STOP"
            return []

        # Execute the window, capture + normalize the new state.
        new = self.material.normalize(self.adapter.execute(action, prev))
        results = [c.evaluate(prev, new) for c in self.checkpoints]
        self.material.persist(self.run_id, new.frame, action, new, results)
        self.state = new

        # Behavior-change loop keyed on forward progress.
        progress = next((r for r in results if r.name == "FORWARD_PROGRESS"), None)
        if progress is not None and not progress.passed:
            self._consecutive_fails += 1
            self._feedback = (
                f"checkpoint {progress.name} failed: {progress.detail}. "
                "An obstacle is likely blocking you — try JUMP (press A)."
            )
            if self._consecutive_fails >= self.escalate_after:
                self.alarms.emit(
                    Alarm(
                        "AGENT_STUCK",
                        Severity.CRITICAL,
                        {"frames_stuck": self._consecutive_fails, "x": new.x},
                        "request human intervention",
                    )
                )
                self.status = "STOP"
            else:
                self.alarms.emit(
                    Alarm(
                        "AGENT_STUCK",
                        Severity.HIGH,
                        {"frames_stuck": self._consecutive_fails, "x": new.x},
                        "feed corrective hint to the worker",
                    )
                )
        else:
            self._consecutive_fails = 0
            self._feedback = None

        return results

    def run(self, max_steps: int = 100) -> None:
        for _ in range(max_steps):
            if self.status != "RUNNING":
                break
            self.step()
