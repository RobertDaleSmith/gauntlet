"""HarnessSession drives the browser-side loop without a WebSocket or browser."""
from harness.session import HarnessSession


def _state(height, lines=0, game_over=False, frame=0):
    return {"frame": frame, "stack_height": height, "lines": lines,
            "score": lines * 100, "holes": 0, "game_over": game_over, "level": 1}


def test_first_observe_returns_an_action_no_checkpoints():
    s = HarnessSession()
    out = s.step(_state(0))
    assert out["type"] == "act"
    assert out["checkpoints"] == []  # nothing to grade yet
    assert out["action"]["buttons"]  # a real controller action


def test_grades_previous_step_and_emits_alarm_when_stack_too_high():
    s = HarnessSession()
    s.step(_state(0))  # first observe -> action
    out = s.step(_state(15, frame=4))  # report a dangerously high stack
    names = [c["name"] for c in out["checkpoints"]]
    assert "STACK_HEIGHT_SAFE" in names
    assert any(not c["passed"] for c in out["checkpoints"])
    assert any(a["type"] == "CHECKPOINT_FAILED" for a in out["alarms"])


def test_game_over_stops_the_session():
    s = HarnessSession()
    s.step(_state(0))
    out = s.step(_state(20, game_over=True, frame=4))
    assert out["type"] == "stopped"
    assert any(a["type"] == "GAME_OVER" for a in out["alarms"])


class _BoomWorker:
    name = "boom"

    def decide(self, state, feedback):
        raise RuntimeError("no API key")


def test_worker_error_fails_safe():
    s = HarnessSession(worker=_BoomWorker())
    out = s.step(_state(0))
    assert out["type"] == "stopped"
    assert any(a["type"] == "WORKER_ERROR" for a in out["alarms"])


def test_observations_after_stop_are_ignored():
    s = HarnessSession()
    s.step(_state(0))
    s.step(_state(20, game_over=True, frame=4))  # -> stopped
    again = s.step(_state(20, game_over=True, frame=8))
    assert again["type"] == "stopped"


def _st(height, holes, frame):
    return {"frame": frame, "stack_height": height, "lines": 0, "score": 0,
            "holes": holes, "game_over": False, "level": 1}


def test_alarm_severity_low_for_holes_only():
    s = HarnessSession()
    s.step(_st(0, 0, 0))
    out = s.step(_st(5, 2, 4))  # holes 0->2 fails NO_NEW_HOLES (LOW); height safe
    cf = [a for a in out["alarms"] if a["type"] == "CHECKPOINT_FAILED"]
    assert cf and cf[0]["severity"] == "LOW"


def test_alarm_severity_high_for_stack_danger():
    s = HarnessSession()
    s.step(_st(0, 0, 0))
    out = s.step(_st(15, 0, 4))  # height 15 fails STACK_HEIGHT_SAFE (HIGH)
    cf = [a for a in out["alarms"] if a["type"] == "CHECKPOINT_FAILED"]
    assert cf and cf[0]["severity"] == "HIGH"
