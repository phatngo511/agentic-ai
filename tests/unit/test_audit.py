"""Tests for audit logging."""

import json

from src.ch05_hitl.audit import AuditLog


def test_record_entry():
    log = AuditLog()
    entry = log.record(actor="agent", action="search", decision="proceed", confidence=0.8)
    assert log.entry_count == 1
    assert entry.actor == "agent"


def test_append_only():
    log = AuditLog()
    log.record(actor="agent", action="search", decision="proceed")
    log.record(actor="human", action="approve", decision="approved")
    assert log.entry_count == 2
    entries = log.entries
    entries.clear()  # clearing the copy should not affect the log
    assert log.entry_count == 2


def test_to_json():
    log = AuditLog()
    log.record(actor="agent", action="search", decision="proceed")
    data = json.loads(log.to_json())
    assert len(data) == 1
    assert data[0]["actor"] == "agent"


def test_to_markdown():
    log = AuditLog()
    log.record(actor="agent", action="triage", decision="escalate", confidence=0.3, risk_level="high")
    md = log.to_markdown()
    assert "| agent |" in md
    assert "triage" in md
