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
