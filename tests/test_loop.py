"""Integration test for the hero beat: stuck -> feedback -> adapt -> clears."""
from harness.adapters import FakeGameAdapter
from harness.loop import HarnessLoop
from workers.scripted import ScriptedWorker


def test_feedback_loop_clears_the_pipe():
    loop = HarnessLoop(FakeGameAdapter(), ScriptedWorker())
    loop.run(max_steps=20)

    # Got past the pipe (started at x=380, pipe at 400).
    assert loop.state.x > FakeGameAdapter.PIPE_X + 10
    # The stuck alarm fired (proves the loop detected + reacted).
    assert any(a.type == "AGENT_STUCK" for a in loop.alarms.history)
    # It recovered via feedback rather than escalating to a human STOP.
    assert loop.status == "RUNNING"


def test_run_is_replayable():
    loop = HarnessLoop(FakeGameAdapter(), ScriptedWorker())
    loop.run(max_steps=10)
    assert len(loop.material.replay(loop.run_id)) >= 1
