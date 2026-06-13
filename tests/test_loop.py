"""Hero beat: reckless stacking -> alarm + feedback -> deliberate placement clears."""
from harness.adapters import FakeTetrisAdapter
from harness.loop import HarnessLoop
from workers.scripted import ScriptedWorker


def test_feedback_loop_recovers_from_high_stack():
    loop = HarnessLoop(FakeTetrisAdapter(), ScriptedWorker())
    loop.run(max_steps=30)

    # The danger checkpoint failed and the harness raised an alarm.
    assert any(a.type == "CHECKPOINT_FAILED" for a in loop.alarms.history)
    # Feedback drove a deliberate placement that cleared at least one line.
    assert loop.state.lines >= 1
    # Recovered rather than escalating to a human STOP.
    assert loop.status == "RUNNING"


def test_run_is_replayable():
    loop = HarnessLoop(FakeTetrisAdapter(), ScriptedWorker())
    loop.run(max_steps=10)
    assert len(loop.material.replay(loop.run_id)) >= 1
