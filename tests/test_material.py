from harness.checkpoints import CheckpointResult
from harness.material import MaterialHandler
from harness.types import Action, GameState


def test_normalize_reads_ram_dict():
    s = MaterialHandler().normalize({"frame": 5, "x": 42, "score": 100, "lives": 2})
    assert (s.frame, s.x, s.score, s.lives) == (5, 42, 100, 2)


def test_persist_and_replay_roundtrip():
    m = MaterialHandler()
    m.persist(
        "run1",
        30,
        Action(("RIGHT",), 30),
        GameState(30, x=10),
        [CheckpointResult("FORWARD_PROGRESS", True, "x 0->10")],
    )
    rows = m.replay("run1")
    assert len(rows) == 1
    assert rows[0]["state"]["x"] == 10
    assert rows[0]["results"][0]["passed"] is True


def test_load_state_at_frame():
    m = MaterialHandler()
    m.persist("run1", 60, Action(("RIGHT",), 30), GameState(60, x=99), [])
    assert m.load_state("run1", 60).x == 99
