"""Test playbook library."""
import pytest
from hornet.playbooks import get_playbook, match_playbook, PLAYBOOKS


def test_get_playbook():
    pb = get_playbook("PB-AUTH-001")
    assert pb is not None
    assert pb.name == "Brute Force Response"
    assert pb.priority.value == "MEDIUM"


def test_get_playbook_not_found():
    pb = get_playbook("PB-NONEXISTENT")
    assert pb is None


def test_match_playbook():
    matches = match_playbook("auth.brute_force")
    assert len(matches) > 0
    assert matches[0].id == "PB-AUTH-001"


def test_match_playbook_no_match():
    matches = match_playbook("unknown.event.type")
    assert len(matches) == 0


def test_playbook_count():
    assert len(PLAYBOOKS) >= 12  # We have at least 12 playbooks
