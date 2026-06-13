from harness.checkpoints import CheckpointResult
from harness.material import MaterialHandler
from harness.types import Action, GameState


def test_normalize_reads_state_dict():
    s = MaterialHandler().normalize(
        {"frame": 5, "score": 100, "lines": 3, "stack_height": 7, "holes": 1}
    )
    assert (s.frame, s.score, s.lines, s.stack_height, s.holes) == (5, 100, 3, 7, 1)


def test_persist_and_replay_roundtrip():
    m = MaterialHandler()
    m.persist(
        "run1",
        4,
        Action(("DROP",), 4),
        GameState(4, score=100, lines=1, stack_height=5),
        [CheckpointResult("STACK_HEIGHT_SAFE", True, "height 5")],
    )
    rows = m.replay("run1")
    assert len(rows) == 1
    assert rows[0]["state"]["lines"] == 1
    assert rows[0]["results"][0]["passed"] is True


def test_load_state_at_frame():
    m = MaterialHandler()
    m.persist("run1", 8, Action(("DROP",), 4), GameState(8, stack_height=9), [])
    assert m.load_state("run1", 8).stack_height == 9
