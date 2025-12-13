"""Unit tests for WebUI session state management."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from parakeet_rocm.webui.core import session as session_mod


@dataclass
class _Job:
    job_id: str
    metrics: dict[str, object] | None


class _JobManager:
    def __init__(self, *, current: _Job | None, last: _Job | None) -> None:
        self._current = current
        self._last = last

    def get_current_job(self) -> _Job | None:
        return self._current

    def get_last_completed_job(self) -> _Job | None:
        return self._last


def test_session_manager_crud() -> None:
    """SessionManager should create, retrieve, update, and delete sessions."""
    manager = session_mod.SessionManager()
    state = manager.create_session()

    retrieved = manager.get_session(state.session_id)
    assert retrieved is state

    state.workflow_state = session_mod.WorkflowState.CONFIGURING
    manager.update_session(state)
    assert (
        manager.get_session(state.session_id).workflow_state
        == session_mod.WorkflowState.CONFIGURING
    )

    assert manager.list_sessions()
    manager.delete_session(state.session_id)
    assert manager.list_sessions() == []


def test_session_manager_update_missing_raises() -> None:
    """Updating a missing session should raise KeyError."""
    manager = session_mod.SessionManager()
    state = session_mod.SessionState(session_id="missing")
    with pytest.raises(KeyError):
        manager.update_session(state)


def test_session_helpers_global_job_manager() -> None:
    """Session helpers should return metrics from current/last jobs."""
    current = _Job(job_id="cur", metrics={"runtime_seconds": 1.0})
    last = _Job(job_id="last", metrics={"runtime_seconds": 2.0})

    session_mod.set_global_job_manager(_JobManager(current=current, last=last))
    assert session_mod.get_current_job_metrics() == {"runtime_seconds": 1.0}
    assert session_mod.get_last_job_metrics() == {"runtime_seconds": 2.0}


def test_session_helpers_no_job_manager() -> None:
    """Session helpers should return None when no global job manager is set."""
    session_mod.set_global_job_manager(None)
    assert session_mod.get_current_job_metrics() is None
    assert session_mod.get_last_job_metrics() is None
