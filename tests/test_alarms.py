from harness.alarms import Alarm, AlarmBus, Severity


def test_alarm_to_dict_has_required_shape():
    a = Alarm("AGENT_STUCK", Severity.HIGH, {"x": 400}, "feed hint")
    d = a.to_dict()
    assert set(d) == {"type", "severity", "context", "recommended_action"}
    assert d["severity"] == "HIGH"


def test_alarm_bus_emits_and_records():
    bus = AlarmBus()
    seen = []
    bus.subscribe(seen.append)
    bus.emit(Alarm("X", Severity.LOW, {}, "noop"))
    assert len(bus.history) == 1 and len(seen) == 1
