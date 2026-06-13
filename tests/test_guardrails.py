from harness.guardrails import (
    AllowedButtons,
    GuardrailSet,
    MaxHoldFrames,
    NoImpossibleCombos,
)
from harness.types import Action, GameState

STATE = GameState(frame=0)


def test_allowed_buttons_blocks_unknown():
    v = AllowedButtons().check(Action(("RIGHT", "JUMP"), 30), STATE)
    assert not v.allowed and v.guardrail == "ALLOWED_BUTTONS"


def test_max_hold_frames_blocks_over_limit():
    assert not MaxHoldFrames(120).check(Action(("RIGHT",), 200), STATE).allowed
    assert MaxHoldFrames(120).check(Action(("RIGHT",), 60), STATE).allowed


def test_no_impossible_combos_blocks_opposites():
    assert not NoImpossibleCombos().check(Action(("LEFT", "RIGHT"), 30), STATE).allowed


def test_guardrail_set_allows_valid_action():
    assert GuardrailSet().validate(Action(("RIGHT", "A"), 30), STATE).allowed


def test_guardrail_set_first_block_wins():
    v = GuardrailSet().validate(Action(("LEFT", "RIGHT"), 999), STATE)
    assert not v.allowed
