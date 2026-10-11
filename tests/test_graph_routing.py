
from src.graph import _ticket_route_for_severity


def test_high_severity_routes_to_ticket():
    assert _ticket_route_for_severity("HIGH") == "draft_ticket"


def test_critical_severity_routes_to_ticket():
    assert _ticket_route_for_severity("CRITICAL") == "draft_ticket"


def test_medium_severity_skips_ticket():
    assert _ticket_route_for_severity("MEDIUM") == "assemble"


def test_low_severity_skips_ticket():
    assert _ticket_route_for_severity("LOW") == "assemble"


def test_unknown_severity_skips_ticket():
    assert _ticket_route_for_severity("UNKNOWN") == "assemble"
