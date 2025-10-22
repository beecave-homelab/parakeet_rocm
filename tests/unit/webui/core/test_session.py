"""Unit tests for core.session module.

Tests session state management for tracking user workflow
state and configuration across UI interactions.
"""

from __future__ import annotations

import pytest

from parakeet_rocm.webui.core.session import (
    SessionManager,
    SessionState,
    WorkflowState,
)


class TestWorkflowState:
    """Test WorkflowState enum."""

    def test_all_states_defined__has_expected_values(self) -> None:
        """WorkflowState should have all expected states."""
        assert WorkflowState.IDLE == "idle"
        assert WorkflowState.FILES_LOADED == "files_loaded"
        assert WorkflowState.CONFIGURING == "configuring"
        assert WorkflowState.VALIDATING == "validating"
        assert WorkflowState.PROCESSING == "processing"
        assert WorkflowState.COMPLETED == "completed"
        assert WorkflowState.ERROR == "error"


class TestSessionState:
    """Test SessionState dataclass."""

    def test_default_state__starts_idle(self) -> None:
        """New session should start in IDLE state."""
        state = SessionState()

        assert state.workflow_state == WorkflowState.IDLE
        assert state.session_id is not None
        assert len(state.session_id) > 0

    def test_unique_session_ids__generates_different_ids(self) -> None:
        """Each session should have a unique ID."""
        state1 = SessionState()
        state2 = SessionState()

        assert state1.session_id != state2.session_id

    def test_initial_files__empty_list(self) -> None:
        """Initial state should have empty file list."""
        state = SessionState()

        assert state.uploaded_files == []

    def test_initial_job_id__none(self) -> None:
        """Initial state should have no job ID."""
        state = SessionState()

        assert state.current_job_id is None

    def test_initial_error__none(self) -> None:
        """Initial state should have no error."""
        state = SessionState()

        assert state.error_message is None


class TestSessionManager:
    """Test SessionManager class."""

    def test_create_session__returns_new_state(self) -> None:
        """Creating session should return new SessionState."""
        manager = SessionManager()

        state = manager.create_session()

        assert isinstance(state, SessionState)
        assert state.workflow_state == WorkflowState.IDLE

    def test_multiple_sessions__tracked_separately(self) -> None:
        """Manager should track multiple sessions."""
        manager = SessionManager()

        state1 = manager.create_session()
        state2 = manager.create_session()

        assert state1.session_id != state2.session_id
        assert manager.get_session(state1.session_id) == state1
        assert manager.get_session(state2.session_id) == state2

    def test_get_session__returns_correct_state(self) -> None:
        """Getting session by ID should return correct state."""
        manager = SessionManager()
        state = manager.create_session()

        retrieved = manager.get_session(state.session_id)

        assert retrieved == state
        assert retrieved.session_id == state.session_id

    def test_get_nonexistent_session__raises_keyerror(self) -> None:
        """Getting non-existent session should raise KeyError."""
        manager = SessionManager()

        with pytest.raises(KeyError):
            manager.get_session("nonexistent-id")

    def test_update_session__modifies_state(self) -> None:
        """Updating session should modify stored state."""
        manager = SessionManager()
        state = manager.create_session()

        # Modify state
        state.workflow_state = WorkflowState.FILES_LOADED
        manager.update_session(state)

        # Retrieve and verify
        retrieved = manager.get_session(state.session_id)
        assert retrieved.workflow_state == WorkflowState.FILES_LOADED

    def test_update_nonexistent_session__raises_keyerror(self) -> None:
        """Updating non-existent session should raise KeyError."""
        manager = SessionManager()
        fake_state = SessionState()
        fake_state.session_id = "nonexistent-id"

        with pytest.raises(KeyError):
            manager.update_session(fake_state)

    def test_delete_session__removes_from_manager(self) -> None:
        """Deleting session should remove it from manager."""
        manager = SessionManager()
        state = manager.create_session()
        session_id = state.session_id

        manager.delete_session(session_id)

        with pytest.raises(KeyError):
            manager.get_session(session_id)

    def test_delete_nonexistent_session__raises_keyerror(self) -> None:
        """Deleting non-existent session should raise KeyError."""
        manager = SessionManager()

        with pytest.raises(KeyError):
            manager.delete_session("nonexistent-id")

    def test_list_sessions__returns_all_sessions(self) -> None:
        """Listing sessions should return all active sessions."""
        manager = SessionManager()

        state1 = manager.create_session()
        state2 = manager.create_session()
        state3 = manager.create_session()

        sessions = manager.list_sessions()

        assert len(sessions) == 3
        assert state1 in sessions
        assert state2 in sessions
        assert state3 in sessions

    def test_list_sessions_empty__returns_empty_list(self) -> None:
        """Listing sessions when empty should return empty list."""
        manager = SessionManager()

        sessions = manager.list_sessions()

        assert sessions == []

    def test_clear_sessions__removes_all_sessions(self) -> None:
        """Clearing sessions should remove all stored sessions."""
        manager = SessionManager()

        manager.create_session()
        manager.create_session()
        manager.create_session()

        manager.clear_sessions()

        assert manager.list_sessions() == []
