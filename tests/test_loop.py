"""Hero beat: reckless stacking -> alarm + feedback -> deliberate placement clears."""
from harness.adapters import FakeTetrisAdapter
from harness.loop import HarnessLoop
from harness.types import Action
from workers.scripted import ScriptedWorker


class _BadWorker:
    name = "bad"

    def decide(self, state, feedback):
        return Action(("LEFT", "RIGHT"), 4)  # always illegal (opposing inputs)


def test_guardrail_deadlock_stops_and_alarms():
    loop = HarnessLoop(FakeTetrisAdapter(), _BadWorker())
    loop.step()
    assert loop.status == "STOP"
    assert any(a.type == "GUARDRAIL_DEADLOCK" for a in loop.alarms.history)


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


class _FlakyWorker:
    name = "flaky"

    def decide(self, state, feedback):
        # illegal first (no feedback), legal once the guardrail feedback arrives
        return Action(("DROP",), 4) if feedback else Action(("LEFT", "RIGHT"), 4)


def test_guardrail_retry_then_succeed():
    loop = HarnessLoop(FakeTetrisAdapter(), _FlakyWorker())
    loop.step()
    assert loop.status == "RUNNING"
    assert any(a.type == "GUARDRAIL_BLOCKED" for a in loop.alarms.history)
    assert not any(a.type == "GUARDRAIL_DEADLOCK" for a in loop.alarms.history)


class _AlwaysDrop:
    name = "always-drop"
    def decide(self, state, feedback):
        return Action(("DROP",), 4)  # reckless: stacks up on the fake adapter


class _Digger:
    name = "digger"
    def decide(self, state, feedback):
        return Action(("LEFT", "DROP"), 4)  # "thoughtful" on the fake -> clears a line


def test_dual_worker_recovery_swaps_and_hands_back():
    loop = HarnessLoop(FakeTetrisAdapter(), _AlwaysDrop(), recovery_worker=_Digger())
    loop.run(max_steps=40)
    types = [a.type for a in loop.alarms.history]
    assert "RECOVERY_SWAP" in types   # harness handed off to recovery
    assert "RECOVERED" in types       # ...and handed back once safe
    assert loop.status == "RUNNING"   # survived instead of escalating to human
    assert loop.state.lines >= 1      # recovery actually cleared lines


def test_no_recovery_worker_escalates_to_human():
    loop = HarnessLoop(FakeTetrisAdapter(), _AlwaysDrop())  # no recovery
    loop.run(max_steps=40)
    assert loop.status == "STOP"
    assert any(a.type == "ESCALATE" for a in loop.alarms.history)
