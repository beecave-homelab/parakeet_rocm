"""Session state management for WebUI.

Provides centralized session state tracking to manage user workflow
state, configuration, and temporary data across UI interactions.
"""

from __future__ import annotations

import enum
import pathlib
import uuid
from dataclasses import dataclass, field


class WorkflowState(str, enum.Enum):  # noqa: UP042
    """WebUI workflow states.

    Tracks the current stage of the transcription workflow
    to enable appropriate UI state and validation.

    Attributes:
        IDLE: Waiting for file upload.
        FILES_LOADED: Files uploaded, ready for configuration.
        CONFIGURING: User adjusting settings.
        VALIDATING: Validating inputs before processing.
        PROCESSING: Transcription in progress.
        COMPLETED: Job finished successfully.
        ERROR: Error occurred during workflow.
    """

    IDLE = "idle"
    FILES_LOADED = "files_loaded"
    CONFIGURING = "configuring"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SessionState:
    """Session state for a single user session.

    Tracks workflow state, uploaded files, configuration, and
    current job information for a user session.

    Attributes:
        session_id: Unique session identifier.
        workflow_state: Current workflow state.
        uploaded_files: List of uploaded file paths.
        current_job_id: ID of current transcription job.
        error_message: Error message if workflow_state is ERROR.

    Examples:
        >>> state = SessionState()
        >>> state.workflow_state
        <WorkflowState.IDLE: 'idle'>

        >>> state.workflow_state = WorkflowState.FILES_LOADED
        >>> state.uploaded_files = [pathlib.Path("audio.wav")]
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_state: WorkflowState = WorkflowState.IDLE
    uploaded_files: list[pathlib.Path] = field(default_factory=list)
    current_job_id: str | None = None
    error_message: str | None = None


class SessionManager:
    """Manages user sessions and workflow state.

    Provides centralized session management with creation, retrieval,
    update, and deletion operations. Tracks multiple concurrent sessions.

    Attributes:
        sessions: Dictionary of active sessions keyed by session_id.

    Examples:
        >>> manager = SessionManager()
        >>> state = manager.create_session()
        >>> state.session_id
        'a1b2c3d4-...'

        >>> retrieved = manager.get_session(state.session_id)
        >>> retrieved.workflow_state
        <WorkflowState.IDLE: 'idle'>
    """

    def __init__(self) -> None:
        """Initialize session manager with empty session storage."""
        self.sessions: dict[str, SessionState] = {}

    def create_session(self) -> SessionState:
        """Create a new user session.

        Returns:
            New SessionState with unique ID.

        Examples:
            >>> manager = SessionManager()
            >>> state = manager.create_session()
            >>> state.workflow_state
            <WorkflowState.IDLE: 'idle'>
        """
        state = SessionState()
        self.sessions[state.session_id] = state
        return state

    def get_session(self, session_id: str) -> SessionState:
        """Retrieve session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            SessionState for the given ID.

        Examples:
            >>> manager = SessionManager()
            >>> state = manager.create_session()
            >>> retrieved = manager.get_session(state.session_id)
            >>> retrieved == state
            True
        """
        return self.sessions[session_id]

    def update_session(self, state: SessionState) -> None:
        """Update an existing session.

        Args:
            state: Updated SessionState object.

        Raises:
            KeyError: If session_id not found.

        Examples:
            >>> manager = SessionManager()
            >>> state = manager.create_session()
            >>> state.workflow_state = WorkflowState.FILES_LOADED
            >>> manager.update_session(state)
        """
        if state.session_id not in self.sessions:
            raise KeyError(f"Session not found: {state.session_id}")
        self.sessions[state.session_id] = state

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session identifier.

        Raises:
            KeyError: If session_id not found.

        Examples:
            >>> manager = SessionManager()
            >>> state = manager.create_session()
            >>> manager.delete_session(state.session_id)
        """
        if session_id not in self.sessions:
            raise KeyError(f"Session not found: {session_id}")
        del self.sessions[session_id]

    def list_sessions(self) -> list[SessionState]:
        """List all active sessions.

        Returns:
            List of all SessionState objects.

        Examples:
            >>> manager = SessionManager()
            >>> manager.create_session()
            >>> manager.create_session()
            >>> len(manager.list_sessions())
            2
        """
        return list(self.sessions.values())

    def clear_sessions(self) -> None:
        """Clear all sessions.

        Removes all stored sessions from the manager.

        Examples:
            >>> manager = SessionManager()
            >>> manager.create_session()
            >>> manager.clear_sessions()
            >>> len(manager.list_sessions())
            0
        """
        self.sessions.clear()
