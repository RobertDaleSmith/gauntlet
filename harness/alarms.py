"""🚨 Alarms pillar — structured failures with a recommended action."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Alarm:
    """A named alarm with context and a recommended action.

    This is the rubric's required shape: type, severity, context, action.
    """

    type: str
    severity: Severity
    context: dict
    recommended_action: str

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity.value,
            "context": self.context,
            "recommended_action": self.recommended_action,
        }


class AlarmBus:
    """Collects alarms and fans them out to subscribers (e.g. the dashboard)."""

    def __init__(self) -> None:
        self._history: list[Alarm] = []
        self._subscribers: list[Callable[[Alarm], None]] = []

    def emit(self, alarm: Alarm) -> Alarm:
        self._history.append(alarm)
        for sub in self._subscribers:
            sub(alarm)
        return alarm

    def subscribe(self, fn: Callable[[Alarm], None]) -> None:
        self._subscribers.append(fn)

    @property
    def history(self) -> list[Alarm]:
        return list(self._history)
