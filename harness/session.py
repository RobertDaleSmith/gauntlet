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
from workers.heuristic import HeuristicWorker


class HarnessSession:
    def __init__(self, worker=None, db_path: str = ":memory:") -> None:
        # Default to the competent worker so "Start" plays well out of the box.
        # Recovery worker (heuristic) is on by default: if the primary agent gets
        # stuck, the harness hands off to it, then hands back — see HarnessLoop.
        self.loop = HarnessLoop(
            NullAdapter(),
            worker or HeuristicWorker(),
            material=MaterialHandler(db_path),
            alarms=AlarmBus(),
            recovery_worker=HeuristicWorker(),
            # The browser steps once per button press, so a recovery worker needs
            # many steps just to walk a piece to the abandoned columns and start
            # clearing. Give it room to actually dig out before escalating.
            recovery_budget=80,
        )
        self._events = []
        self.loop.alarms.subscribe(self._events.append)
        self.prev = None
        self.last_action = None
        self.last_frame = None

    def set_worker(self, worker) -> None:
        self.loop.set_primary(worker)

    def set_recovery(self, on: bool) -> None:
        self.loop.recovery_worker = HeuristicWorker() if on else None

    def _drain(self) -> list[dict]:
        evs = [a.to_dict() for a in self._events]
        self._events.clear()
        return evs

    def step(self, state_dict: dict, frame: str | None = None,
             vision: dict | None = None) -> dict:
        """Process one observation from the browser; return the next message.

        `state_dict` is ground truth (the referee grades and persists from it).
        `vision`, when present, is a board reconstructed from the rendered pixels
        (no game state) — the *agent* perceives that instead, while the referee
        still uses ground truth. This is how a worker plays "from video alone".
        """
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

        # Agent perception: a pixel-derived board (vision-only) if provided, else
        # ground truth. The referee above already graded on ground truth.
        worker_state = new
        if vision and vision.get("board"):
            from dataclasses import replace
            worker_state = replace(new, raw={
                **new.raw,
                "board": vision.get("board"),
                "current": vision.get("current"),
                "next": vision.get("next"),
            })

        try:
            action = self.loop.decide(worker_state)
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
            "model": getattr(self.loop.worker, "model", None),
            "perception": getattr(self.loop.worker, "perception", None),
            "action": {"buttons": list(action.buttons), "hold_frames": action.hold_frames},
            "checkpoints": checkpoints,
            "alarms": self._drain(),
        }
