"""Tests for session and task state management."""

import pytest

from code.ch03.state import SessionState, TaskState


def test_session_state_tracks_history():
    state = SessionState()
    state.add_query("What is X?")
    state.add_answer("X is Y.")
    assert len(state.history) == 2


def test_session_state_has_turn_count():
    state = SessionState()
    assert state.turn_count == 0
    state.add_query("Q1")
    state.add_answer("A1")
    assert state.turn_count == 1


def test_task_state_tracks_steps():
    task = TaskState(task_id="t1", query="What is X?")
    task.add_step("retrieve", {"query": "X"}, "found 3 chunks")
    assert len(task.steps) == 1
    assert task.steps[0]["action"] == "retrieve"


def test_task_state_is_complete():
    task = TaskState(task_id="t1", query="What is X?")
    assert task.is_complete is False
    task.mark_complete("X is Y.", confidence=0.9)
    assert task.is_complete is True
    assert task.confidence == 0.9


def test_task_state_budget_tracking():
    task = TaskState(task_id="t1", query="Q", max_steps=3)
    assert task.budget_remaining == 3
    task.add_step("s1", {}, "r1")
    assert task.budget_remaining == 2


def test_task_state_over_budget():
    task = TaskState(task_id="t1", query="Q", max_steps=1)
    task.add_step("s1", {}, "r1")
    assert task.is_over_budget is True
