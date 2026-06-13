"""Per-connection harness session for the browser-driven (vision) path.

The browser is the executor: it renders the game (the video the agent sees) and
applies controller inputs. Each step it sends the new state + frame; the session
runs the pillars (guardrails/checkpoints/alarms) and returns the next action plus
the events to show on the dashboard. The agent only ever receives the frame; the
ground-truth state is used by the referee for grading.
"""
from __future__ import annotations

from harness.adapters import NullAdapter
from harness.alarms import AlarmBus
from harness.loop import HarnessLoop
from harness.material import MaterialHandler
from workers.scripted import ScriptedWorker


class HarnessSession:
    def __init__(self, worker=None, db_path: str = ":memory:") -> None:
        self.loop = HarnessLoop(
            NullAdapter(),
            worker or ScriptedWorker(),
            material=MaterialHandler(db_path),
            alarms=AlarmBus(),
        )
        self._events = []
        self.loop.alarms.subscribe(self._events.append)
        self.prev = None
        self.last_action = None
        self.last_frame = None

    def set_worker(self, worker) -> None:
        self.loop.worker = worker

    def _drain(self) -> list[dict]:
        evs = [a.to_dict() for a in self._events]
        self._events.clear()
        return evs

    def step(self, state_dict: dict, frame: str | None = None) -> dict:
        """Process one observation from the browser; return the next message."""
        if self.loop.status != "RUNNING":
            return {"type": "stopped", "status": self.loop.status,
                    "checkpoints": [], "alarms": self._drain()}
        self.last_frame = frame
        new = self.loop.material.normalize(state_dict)

        # Grade the previous action's outcome (skip on the very first observe).
        results = []
        if self.prev is not None and self.last_action is not None:
            results = self.loop.observe(self.prev, new, self.last_action)
        else:
            self.loop.state = new

        checkpoints = [r.to_dict() for r in results]

        if self.loop.status != "RUNNING":
            return {"type": "stopped", "status": self.loop.status,
                    "checkpoints": checkpoints, "alarms": self._drain()}

        # Give vision workers the frame out-of-band (keeps the Worker protocol clean).
        if frame is not None and hasattr(self.loop.worker, "set_frame"):
            self.loop.worker.set_frame(frame)

        try:
            action = self.loop.decide(new)
        except Exception as e:  # worker misconfig (e.g. missing API key) — fail safe
            self.loop.status = "STOP"
            return {"type": "stopped", "status": "STOP", "error": str(e),
                    "checkpoints": checkpoints,
                    "alarms": self._drain() + [{
                        "type": "WORKER_ERROR", "severity": "CRITICAL",
                        "context": {"error": str(e)},
                        "recommended_action": "check worker config / API key",
                    }]}

        if action is None:
            return {"type": "stopped", "status": self.loop.status,
                    "checkpoints": checkpoints, "alarms": self._drain()}

        self.prev = new
        self.last_action = action
        return {
            "type": "act",
            "run_id": self.loop.run_id,
            "worker": self.loop.worker.name,
            "action": {"buttons": list(action.buttons), "hold_frames": action.hold_frames},
            "checkpoints": checkpoints,
            "alarms": self._drain(),
        }
