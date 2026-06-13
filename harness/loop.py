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
        escalation_checkpoint: str | None = None,
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
        # Which checkpoint's repeated failure escalates to a human STOP.
        # Defaults to the first (primary) checkpoint.
        self.escalation_checkpoint = escalation_checkpoint or (
            self.checkpoints[0].name if self.checkpoints else None
        )
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

        # Terminal failure: the game ended.
        if new.game_over:
            self.alarms.emit(
                Alarm(
                    "GAME_OVER",
                    Severity.CRITICAL,
                    {"score": new.score, "lines": new.lines},
                    "reset the run or request human intervention",
                )
            )
            self.status = "STOP"
            return results

        # Behavior-change loop: failed checkpoints become feedback for the agent.
        fails = [r for r in results if not r.passed]
        primary_failed = any(
            not r.passed and r.name == self.escalation_checkpoint for r in results
        )
        self._consecutive_fails = self._consecutive_fails + 1 if primary_failed else 0

        if fails:
            self._feedback = (
                "checkpoints failed: "
                + "; ".join(f"{r.name} ({r.detail})" for r in fails)
                + ". Adjust your strategy."
            )
            if primary_failed and self._consecutive_fails >= self.escalate_after:
                self.alarms.emit(
                    Alarm(
                        "ESCALATE",
                        Severity.CRITICAL,
                        {
                            "checkpoint": self.escalation_checkpoint,
                            "consecutive_fails": self._consecutive_fails,
                        },
                        "request human intervention",
                    )
                )
                self.status = "STOP"
            else:
                self.alarms.emit(
                    Alarm(
                        "CHECKPOINT_FAILED",
                        Severity.HIGH,
                        {"failed": [r.name for r in fails], "frame": new.frame},
                        "feed corrective hint to the worker",
                    )
                )
        else:
            self._feedback = None

        return results

    def run(self, max_steps: int = 100) -> None:
        for _ in range(max_steps):
            if self.status != "RUNNING":
                break
            self.step()
