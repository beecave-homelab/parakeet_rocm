# Gradio WebUI Sub-Module - Complete Redesign

**Status**: Planning  
**Created**: 2025-10-16  
**Target Version**: v0.9.0  
**Approach**: Ground-up redesign (not refactoring POC)

---

## Executive Summary

Design and implement a production-ready Gradio WebUI sub-module from scratch for the `parakeet_rocm` package, following modern web app patterns and the project's architectural principles.

**Design Philosophy**:

- **Fresh start**: Not copying the POC script; designing from first principles
- **Modern UX**: Intuitive, responsive interface with progressive disclosure
- **Production-ready**: Proper error handling, validation, and user feedback
- **Extensible**: Easy to add features like real-time streaming, batch queues
- **Developer-friendly**: Clean separation of concerns, testable components

**Current State**:

- POC script exists in `scripts/` (reference only, won't be copied)
- Gradio already in optional dependencies (`webui` group)

**Target State**:

- Professional `parakeet_rocm/webui/` sub-module
- Modern, intuitive UI with superior UX
- Integrated CLI command: `parakeet-rocm webui`
- Comprehensive documentation and tests

---

## Architecture Design - Fresh Approach

### 1. Module Structure

```text
parakeet_rocm/
├── webui/                          # WebUI sub-module
│   ├── __init__.py                # Public API: build_app, launch_app
│   ├── app.py                     # Application factory and launcher
│   ├── core/                      # Core business logic
│   │   ├── __init__.py
│   │   ├── session.py             # Session state management
│   │   ├── job_manager.py         # Transcription job orchestration
│   │   └── result_handler.py      # Result processing and formatting
│   ├── ui/                        # UI layer (presentation)
│   │   ├── __init__.py
│   │   ├── pages/                 # Page-based organization
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # Main transcription page
│   │   │   └── settings.py        # Advanced settings page (tabs)
│   │   ├── components/            # Reusable UI components
│   │   │   ├── __init__.py
│   │   │   ├── file_uploader.py   # Smart file upload widget
│   │   │   ├── config_panel.py    # Configuration panel
│   │   │   ├── progress_tracker.py # Real-time progress display
│   │   │   └── result_viewer.py   # Result display and download
│   │   └── theme.py               # Theme configuration and styling
│   ├── validation/                # Input validation layer
│   │   ├── __init__.py
│   │   ├── file_validator.py      # File validation rules
│   │   ├── config_validator.py    # Configuration validation
│   │   └── schemas.py             # Pydantic validation schemas
│   └── utils/                     # WebUI-specific utilities
│       ├── __init__.py
│       ├── formatters.py          # Output formatters for display
│       └── presets.py             # Configuration presets
```

### 2. Design Principles

#### **Modern Web App Patterns**

**Page-Based Architecture**:

- Gradio Tabs for multi-page experience
- Main page: Simple, focused transcription workflow
- Settings page: Advanced configuration (collapsible groups)
- Results page: History and output management

**Component-Based UI**:

- Reusable, composable UI components
- Each component is self-contained with clear inputs/outputs
- Easy to test and maintain independently

**State Management**:

- Centralized session state using Gradio State
- Clean separation between UI state and business logic
- Predictable data flow

#### **Architectural Layers**

```text
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  (ui/pages/, ui/components/)            │
│  - User interface components            │
│  - Event binding                        │
│  - Visual feedback                      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Business Logic Layer            │
│  (core/job_manager, core/session)       │
│  - Transcription orchestration          │
│  - State management                     │
│  - Error handling                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Validation Layer                │
│  (validation/)                          │
│  - Input validation (Pydantic)          │
│  - File validation                      │
│  - Configuration validation             │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Domain Layer                    │
│  (parakeet_rocm.transcription)          │
│  - Transcription engine                 │
│  - Model management                     │
│  - Audio processing                     │
└─────────────────────────────────────────┘
```

#### **Protocol-Oriented Design**

```python
class TranscriptionService(Protocol):
    """Protocol for transcription service."""
    def transcribe(
        self,
        files: list[pathlib.Path],
        config: TranscriptionConfig,
    ) -> TranscriptionResult: ...

class ResultHandler(Protocol):
    """Protocol for result handling."""
    def format_output(
        self,
        result: TranscriptionResult,
        format_type: str,
    ) -> str: ...
```

#### **SOLID Principles Applied**

- **Single Responsibility**: Each component has one clear purpose
- **Open/Closed**: Extensible via protocols and dependency injection
- **Liskov Substitution**: Protocol-based design ensures substitutability
- **Interface Segregation**: Small, focused protocols
- **Dependency Inversion**: Depend on abstractions (protocols), not concretions

### 3. User Experience Design

#### **Progressive Disclosure**

```text
┌─────────────────────────────────────────────────┐
│  🎤 Parakeet-NEMO ASR WebUI            [⚙️][🌓] │
├─────────────────────────────────────────────────┤
│                                                 │
│  📁 Upload Audio/Video Files                    │
│  ┌─────────────────────────────────────────┐   │
│  │  Drag & Drop or Click to Upload        │   │
│  │  Supports: MP3, WAV, MP4, FLAC, etc.   │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  🎯 Quick Start Presets                         │
│  [Fast] [Balanced] [High Quality] [Custom]     │
│                                                 │
│  ⚡ Advanced Settings (click to expand)         │
│                                                 │
│  [🚀 Start Transcription]                       │
│                                                 │
│  📊 Progress                                    │
│  ▓▓▓▓▓▓▓▓▓▓░░░░░░░ 65% - Processing file 2/3  │
│                                                 │
│  ✅ Results                                     │
│  📄 output_file_1.srt [View] [Download]        │
│  📄 output_file_2.srt [View] [Download]        │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Key UX Principles**:

1. **Simple by default**: Core workflow visible immediately
2. **Power when needed**: Advanced options hidden but accessible
3. **Clear feedback**: Real-time progress, clear error messages
4. **Forgiving**: Easy to recover from errors
5. **Responsive**: Works on different screen sizes

#### **Workflow States**

```python
class WorkflowState(str, enum.Enum):
    """WebUI workflow states."""
    IDLE = "idle"                    # Waiting for files
    FILES_LOADED = "files_loaded"    # Files uploaded, ready to configure
    CONFIGURING = "configuring"      # User adjusting settings
    VALIDATING = "validating"        # Validating inputs
    PROCESSING = "processing"        # Transcription in progress
    COMPLETED = "completed"          # Job finished successfully
    ERROR = "error"                  # Error occurred
```

### 4. Key Components

#### **app.py** - Application Factory

```python
"""Gradio WebUI application factory.

Builds and configures the complete web application using a
page-based architecture with dependency injection.
"""

from __future__ import annotations

import gradio as gr

from parakeet_rocm.webui.core.job_manager import JobManager
from parakeet_rocm.webui.core.session import SessionManager
from parakeet_rocm.webui.ui.pages.main import MainPage
from parakeet_rocm.webui.ui.theme import configure_theme
from parakeet_rocm.utils.constant import (
    GRADIO_ANALYTICS_ENABLED,
    GRADIO_MAX_THREADS,
    GRADIO_SERVER_NAME,
    GRADIO_SERVER_PORT,
)


def build_app(
    *,
    job_manager: JobManager | None = None,
    analytics_enabled: bool = GRADIO_ANALYTICS_ENABLED,
) -> gr.Blocks:
    """Build the Gradio WebUI application.
    
    Uses dependency injection for testability and follows a
    page-based architecture pattern.
    
    Args:
        job_manager: Job manager instance (creates default if None).
        analytics_enabled: Enable Gradio analytics tracking.
    
    Returns:
        Configured Gradio Blocks application ready to launch.
    
    Examples:
        >>> app = build_app()
        >>> app.launch()
    """
    # Initialize dependencies
    if job_manager is None:
        job_manager = JobManager()
    
    session_manager = SessionManager()
    theme = configure_theme()
    
    # Build application
    with gr.Blocks(
        title="Parakeet-NEMO ASR",
        theme=theme,
        analytics_enabled=analytics_enabled,
        css=".gradio-container { max-width: 1200px; margin: auto; }",
    ) as app:
        # Create session state
        session_state = gr.State(session_manager.create_session())
        
        # Build main page
        main_page = MainPage(job_manager, session_state)
        main_page.render()
    
    return app


def launch_app(
    *,
    server_name: str = GRADIO_SERVER_NAME,
    server_port: int = GRADIO_SERVER_PORT,
    share: bool = False,
    debug: bool = False,
    max_threads: int = GRADIO_MAX_THREADS,
) -> None:
    """Launch the Gradio WebUI application.
    
    Builds and starts the web server with specified configuration.
    
    Args:
        server_name: Server hostname or IP address.
        server_port: Server port number.
        share: Create public Gradio share link.
        debug: Enable debug mode with verbose logging.
        max_threads: Maximum number of worker threads.
    
    Raises:
        OSError: If port is already in use.
        RuntimeError: If Gradio fails to initialize.
    
    Examples:
        >>> # Launch on localhost
        >>> launch_app()
        
        >>> # Launch with public sharing
        >>> launch_app(share=True)
        
        >>> # Custom port
        >>> launch_app(server_port=8080)
    """
    app = build_app()
    
    print(f"🚀 Launching Parakeet-NEMO WebUI on {server_name}:{server_port}")
    
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        debug=debug,
        show_error=True,
        max_threads=max_threads,
        quiet=not debug,
    )
```

#### **core/job_manager.py** - Job Orchestration

```python
"""Transcription job management and orchestration.

Handles the lifecycle of transcription jobs from submission
through completion, including progress tracking and error handling.
"""

from __future__ import annotations

import enum
import pathlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from parakeet_rocm.transcription import cli_transcribe
from parakeet_rocm.webui.validation.config_validator import TranscriptionConfig


class JobStatus(str, enum.Enum):
    """Status of a transcription job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TranscriptionJob:
    """Represents a transcription job.
    
    Attributes:
        job_id: Unique job identifier.
        files: Input audio/video files.
        config: Transcription configuration.
        status: Current job status.
        progress: Progress percentage (0-100).
        outputs: Generated output file paths.
        error: Error message if status is FAILED.
        created_at: Job creation timestamp.
        completed_at: Job completion timestamp.
    """
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    files: list[pathlib.Path] = field(default_factory=list)
    config: TranscriptionConfig | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    outputs: list[pathlib.Path] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


class JobManager:
    """Manages transcription job lifecycle.
    
    Attributes:
        transcribe_fn: Transcription function (injected).
        jobs: Active jobs keyed by job_id.
    """
    
    def __init__(self, transcribe_fn: Callable = cli_transcribe) -> None:
        """Initialize job manager.
        
        Args:
            transcribe_fn: Transcription function to use.
        """
        self.transcribe_fn = transcribe_fn
        self.jobs: dict[str, TranscriptionJob] = {}
    
    def submit_job(
        self,
        files: list[pathlib.Path],
        config: TranscriptionConfig,
    ) -> TranscriptionJob:
        """Submit a new transcription job.
        
        Args:
            files: Input files to transcribe.
            config: Validated transcription configuration.
        
        Returns:
            Created job object.
        """
        job = TranscriptionJob(files=files, config=config)
        self.jobs[job.job_id] = job
        return job
    
    def run_job(self, job_id: str) -> TranscriptionJob:
        """Execute a transcription job.
        
        Args:
            job_id: ID of job to run.
        
        Returns:
            Updated job object.
        
        Raises:
            KeyError: If job_id not found.
        """
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        
        try:
            # Execute transcription
            outputs = self.transcribe_fn(
                audio_files=job.files,
                model_name=job.config.model_name,
                output_dir=job.config.output_dir,
                output_format=job.config.output_format,
                batch_size=job.config.batch_size,
                chunk_len_sec=job.config.chunk_len_sec,
                word_timestamps=job.config.word_timestamps,
                stabilize=job.config.stabilize,
                vad=job.config.vad,
                demucs=job.config.demucs,
                vad_threshold=job.config.vad_threshold,
                overwrite=job.config.overwrite,
                verbose=False,
                quiet=True,
                no_progress=True,
                fp16=job.config.fp16,
                fp32=job.config.fp32,
            )
            
            # Update job
            job.outputs = outputs
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.completed_at = datetime.now()
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()
        
        return job
    
    def get_job(self, job_id: str) -> TranscriptionJob:
        """Retrieve job by ID.
        
        Args:
            job_id: Job identifier.
        
        Returns:
            Job object.
        
        Raises:
            KeyError: If job not found.
        """
        return self.jobs[job_id]
    
    def list_jobs(self) -> list[TranscriptionJob]:
        """List all jobs.
        
        Returns:
            List of all jobs, newest first.
        """
        return sorted(
            self.jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )
```

---

## Modern WebUI Features

### Component-Based Architecture

Each UI component is self-contained, reusable, and testable:

- **FileUploader**: Smart upload with validation and preview
- **ConfigPanel**: Collapsible configuration with presets
- **ProgressTracker**: Real-time progress display
- **ResultViewer**: Result display with download buttons

### Validation with Pydantic

All inputs validated using Pydantic schemas:

- Type safety
- Range validation
- Custom validators
- Clear error messages

### Session Management

Centralized session state:

- Workflow tracking
- Job history
- Temporary config storage

### Job Lifecycle

Full job management:

- Submit → Validate → Execute → Complete
- Status tracking
- Error handling
- Progress updates

---

## Implementation Steps | Core

### Phase 1: Core (Days 1-5)

1. **Create directory structure**

   ```bash
   mkdir -p parakeet_rocm/webui/{core,ui/{pages,components},validation,utils}
   touch parakeet_rocm/webui/__init__.py
   # ... create all __init__.py files
   ```

2. **Implement core modules**
   - `core/job_manager.py` - Job orchestration
   - `core/session.py` - Session management
   - `validation/schemas.py` - Pydantic models
   - `validation/file_validator.py` - File validation

3. **Write tests**

   ```bash
   pdm run pytest tests/unit/webui/ -v
   ```

### Phase 2: UI Components (Days 6-10)

1. **Implement UI components**
   - `ui/theme.py` - Theme configuration
   - `ui/components/file_uploader.py`
   - `ui/components/config_panel.py`
   - `ui/components/progress_tracker.py`
   - `ui/components/result_viewer.py`

2. **Implement pages**
   - `ui/pages/main.py` - Main transcription page

3. **Implement utilities**
   - `utils/presets.py` - Configuration presets
   - `utils/formatters.py` - Output formatters

### Phase 3: Integration (Days 11-15)

1. **CLI integration**

   Add to `parakeet_rocm/cli.py`:

   ```python
   @app.command()
   def webui(
       host: str = GRADIO_SERVER_NAME,
       port: int = GRADIO_SERVER_PORT,
       share: bool = False,
       debug: bool = False,
   ) -> None:
       \"\"\"Launch the Gradio WebUI interface.\"\"\"
       from importlib import import_module
       
       webui_app = import_module("parakeet_rocm.webui.app")
       webui_app.launch_app(
           server_name=host,
           server_port=port,
           share=share,
           debug=debug,
       )
   ```

2. **Environment variables**

   Add to `utils/constant.py`:

   ```python
   GRADIO_MAX_THREADS: Final[int] = int(os.getenv("GRADIO_MAX_THREADS", "40"))
   GRADIO_SERVER_NAME: Final[str] = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
   GRADIO_SERVER_PORT: Final[int] = int(os.getenv("GRADIO_SERVER_PORT", "7861"))
   ```

3. **Example layout builder function**

   ```python
   def build_main_layout(handler: TranscriptionHandler) -> None:
    """Build the main WebUI layout.

    Args:
        handler: Transcription handler instance.
    """
    _build_header()
    inputs = _build_input_section()
    controls = _build_control_sections()
    presets = _build_preset_section()
    outputs = _build_output_section()
    
    # Wire up event handlers
    _connect_handlers(handler, inputs, controls, presets, outputs)


    def _build_header() -> None:
    """Build header section with title and theme toggle."""
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("## Parakeet‑NEMO ASR WebUI")
            gr.Markdown(
                "**Upload audio/video and configure transcription settings.**"
            )
        with gr.Column(scale=1, min_width=150):
            gr.Button("Toggle", elem_id="theme-toggle-btn", variant="secondary")

    def _build_input_section() -> dict[str, gr.Component]:
    """Build input section for files and model selection.

    Returns:
        Dictionary mapping component names to Gradio components.
    """
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### Input & Model")
            with gr.Column(elem_classes=["group-box"]):
                files = gr.File(
                    label="Upload Audio / Video",
                    file_count="multiple",
                    type="filepath",
                )
                model_name = gr.Textbox(
                    label="Model Name or Path",
                    value=PARAKEET_MODEL_NAME,
                )
    
    return {"files": files, "model_name": model_name}

    def _build_control_sections() -> dict[str, gr.Component]:
    """Build collapsible control sections.

    Returns:
        Dictionary of all control components.
    """
    controls = {}
    
    # Output settings accordion
    with gr.Accordion("Output Settings", open=False):
        controls.update(_build_output_controls())
    
    # Transcription controls accordion
    with gr.Accordion("Transcription Controls", open=False):
        controls.update(_build_transcription_controls())
    
    # Execution flags accordion
    with gr.Accordion("Execution Flags", open=False):
        controls.update(_build_execution_controls())
    
    return controls


    # ... Additional layout helper functions

   ```

#### **ui/presets.py** - Preset Configurations

```python
"""WebUI preset configurations."""

from __future__ import annotations

from typing import Any

from parakeet_rocm.utils.constant import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    PARAKEET_MODEL_NAME,
)


class PresetConfig:
    """Configuration preset for common use cases."""
    
    def __init__(self, name: str, **kwargs: Any) -> None:
        """Initialize preset configuration.
        
        Args:
            name: Preset name.
            **kwargs: Configuration parameters.
        """
        self.name = name
        self.config = kwargs
    
    def to_tuple(self) -> tuple[Any, ...]:
        """Convert config to tuple for Gradio outputs."""
        return tuple(self.config.values())


# Define presets
DEFAULT_PRESET = PresetConfig(
    name="default",
    model_name=PARAKEET_MODEL_NAME,
    batch_size=DEFAULT_BATCH_SIZE,
    chunk_len_sec=DEFAULT_CHUNK_LEN_SEC,
    stream=False,
    fp16=True,
    fp32=False,
    # ... other default values
)

HIGH_QUALITY_PRESET = PresetConfig(
    name="high_quality",
    batch_size=4,
    chunk_len_sec=300,
    word_timestamps=True,
    highlight_words=True,
    # ... other high-quality settings
)

STREAMING_PRESET = PresetConfig(
    name="streaming",
    stream=True,
    stream_chunk_sec=5,
    batch_size=8,
    # ... other streaming settings
)
```

#### **styles.py** - Styling and Themes

```python
"""WebUI styling and theming."""

from __future__ import annotations

CUSTOM_CSS = """
:root {
  --bg:#f5f7fa;
  --card:#ffffff;
  --fg:#1f2937;
  --muted:#6b7280;
  --radius:10px;
  --shadow:0 12px 30px -4px rgba(31,41,55,0.15);
  --border:1px solid rgba(0,0,0,0.05);
}
/* ... rest of CSS ... */
"""

CUSTOM_JS = """
(function(){
    const stored = localStorage.getItem("parakeet-theme") || "light";
    function setTheme(t) {
        document.documentElement.setAttribute("data-theme", t);
        localStorage.setItem("parakeet-theme", t);
        const btn = document.getElementById("theme-toggle-btn");
        if (btn) btn.textContent = t === "dark" ? "Light Mode" : "Dark Mode";
    }
    setTheme(stored);
    /* ... rest of JS ... */
})();
"""
```

#### **validation.py** - Input Validation

```python
"""WebUI input validation."""

from __future__ import annotations

import pathlib
from typing import Any


class ValidationError(ValueError):
    """Raised when validation fails."""
    pass


def validate_files(files: list[str]) -> list[pathlib.Path]:
    """Validate uploaded file paths.
    
    Args:
        files: List of file path strings.
        
    Returns:
        List of validated Path objects.
        
    Raises:
        ValidationError: If validation fails.
    """
    if not files:
        raise ValidationError("No files provided")
    
    paths = []
    for f in files:
        path = pathlib.Path(f)
        if not path.exists():
            raise ValidationError(f"File not found: {path}")
        if not path.is_file():
            raise ValidationError(f"Not a file: {path}")
        paths.append(path)
    
    return paths


def validate_output_dir(output_dir: str) -> pathlib.Path:
    """Validate output directory path.
    
    Args:
        output_dir: Output directory path string.
        
    Returns:
        Validated Path object.
        
    Raises:
        ValidationError: If validation fails.
    """
    path = pathlib.Path(output_dir)
    
    # Create if doesn't exist
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ValidationError(f"Cannot create directory: {e}") from e
    
    if not path.is_dir():
        raise ValidationError(f"Not a directory: {path}")
    
    return path


def validate_batch_size(batch_size: int) -> int:
    """Validate batch size parameter.
    
    Args:
        batch_size: Batch size value.
        
    Returns:
        Validated batch size.
        
    Raises:
        ValidationError: If validation fails.
    """
    if not isinstance(batch_size, int):
        raise ValidationError(f"Batch size must be an integer, got {type(batch_size)}")
    
    if batch_size < 1:
        raise ValidationError(f"Batch size must be >= 1, got {batch_size}")
    
    if batch_size > 128:
        raise ValidationError(f"Batch size too large (max 128), got {batch_size}")
    
    return batch_size
```

---

## Implementation Steps | Module

### Phase 1: Module Structure (Day 1)

1. **Create directory structure**

   ```bash
   mkdir -p parakeet_rocm/webui/ui
   touch parakeet_rocm/webui/__init__.py
   touch parakeet_rocm/webui/ui/__init__.py
   ```

2. **Create core module files**
   - `parakeet_rocm/webui/app.py`
   - `parakeet_rocm/webui/handlers.py`
   - `parakeet_rocm/webui/styles.py`
   - `parakeet_rocm/webui/validation.py`

3. **Create UI module files**
   - `parakeet_rocm/webui/ui/components.py`
   - `parakeet_rocm/webui/ui/layouts.py`
   - `parakeet_rocm/webui/ui/presets.py`

### Phase 2: Refactor Existing Code (Day 2)

1. **Extract and modularize from `scripts/parakeet_gradio_app.py`**
   - Move CSS/JS to `styles.py`
   - Move UI building logic to `ui/layouts.py`
   - Move preset logic to `ui/presets.py`
   - Move business logic to `handlers.py`
   - Create main app builder in `app.py`

2. **Add proper type hints and docstrings**
   - Follow Google-style docstrings
   - Add full type annotations
   - Document all public APIs

3. **Add input validation**
   - Implement validation functions in `validation.py`
   - Add error handling in handlers

### Phase 3: CLI Integration (Day 2-3)

1. **Add `webui` command to CLI**

   In `parakeet_rocm/cli.py`:

   ```python
   @app.command()
   def webui(
       server_name: Annotated[
           str,
           typer.Option(
               "--host",
               help="Server hostname or IP address.",
           ),
       ] = GRADIO_SERVER_NAME,
       server_port: Annotated[
           int,
           typer.Option(
               "--port",
               help="Server port number.",
           ),
       ] = GRADIO_SERVER_PORT,
       share: Annotated[
           bool,
           typer.Option(
               "--share",
               help="Create public Gradio share link.",
           ),
       ] = False,
       debug: Annotated[
           bool,
           typer.Option(
               "--debug",
               help="Enable debug mode.",
           ),
       ] = False,
   ) -> None:
       """Launch the Gradio WebUI interface.
       
       Args:
           server_name: Server hostname/IP.
           server_port: Server port.
           share: Enable public sharing.
           debug: Enable debug mode.
       """
       # Lazy import to avoid loading Gradio unless needed
       from importlib import import_module
       
       webui_app = import_module("parakeet_rocm.webui.app")
       
       webui_app.launch_app(
           server_name=server_name,
           server_port=server_port,
           share=share,
           debug=debug,
       )
   ```

2. **Update `__init__.py` exports**

   ```python
   # parakeet_rocm/webui/__init__.py
   """Gradio WebUI sub-module for Parakeet-ROCm."""
   
   from parakeet_rocm.webui.app import build_app, launch_app
   
   __all__ = ["build_app", "launch_app"]
   ```

### Phase 4: Environment Variables (Day 3)

Add WebUI-specific configuration to `utils/constant.py`:

```python
# WebUI configuration
GRADIO_SERVER_PORT: Final[int] = int(os.getenv("GRADIO_SERVER_PORT", "7861"))
GRADIO_SERVER_NAME: Final[str] = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_ANALYTICS_ENABLED: Final[bool] = (
    os.getenv("GRADIO_ANALYTICS_ENABLED", "False").lower() == "true"
)
GRADIO_SHARE_ENABLED: Final[bool] = (
    os.getenv("GRADIO_SHARE_ENABLED", "False").lower() == "true"
)
GRADIO_MAX_THREADS: Final[int] = int(os.getenv("GRADIO_MAX_THREADS", "40"))
```

Update `.env.example`:

```bash
# Gradio WebUI Configuration
GRADIO_SERVER_PORT=7861
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_ANALYTICS_ENABLED=False
GRADIO_SHARE_ENABLED=False
GRADIO_MAX_THREADS=40
```

### Phase 5: Tests (Day 4)

Following the `/test-suite` workflow, create comprehensive tests:

#### **Unit Tests**

```text
tests/unit/webui/
├── __init__.py
├── test_handlers.py
├── test_validation.py
├── test_app_builder.py
└── test_presets.py
```

Example: `tests/unit/webui/test_handlers.py`

```python
"""Unit tests for WebUI handlers."""

from __future__ import annotations

import pathlib
from unittest.mock import Mock

import pytest

from parakeet_rocm.webui.handlers import TranscriptionHandler


def test_handler_initialization() -> None:
    """Test handler initializes with transcription function."""
    mock_fn = Mock()
    handler = TranscriptionHandler(transcribe_fn=mock_fn)
    
    assert handler.transcribe_fn is mock_fn


def test_handle_transcription_success(tmp_path: pathlib.Path) -> None:
    """Test successful transcription handling."""
    # Create test files
    test_file = tmp_path / "test.wav"
    test_file.touch()
    
    # Mock transcribe function
    mock_fn = Mock(return_value=[tmp_path / "output.txt"])
    handler = TranscriptionHandler(transcribe_fn=mock_fn)
    
    # Call handler
    result = handler.handle_transcription(
        files=[str(test_file)],
        model_name="test-model",
        output_dir=str(tmp_path),
        output_format="txt",
    )
    
    # Verify
    assert len(result) == 1
    mock_fn.assert_called_once()


def test_handle_transcription_no_files() -> None:
    """Test error when no files provided."""
    mock_fn = Mock()
    handler = TranscriptionHandler(transcribe_fn=mock_fn)
    
    with pytest.raises(ValueError, match="No files provided"):
        handler.handle_transcription(
            files=[],
            model_name="test-model",
            output_dir="/tmp",
            output_format="txt",
        )


def test_validate_precision_both_enabled() -> None:
    """Test precision validation when both flags enabled."""
    handler = TranscriptionHandler(Mock())
    
    fp16, fp32 = handler.validate_precision(fp16=True, fp32=True)
    
    assert fp16 is True
    assert fp32 is False


def test_validate_precision_normal() -> None:
    """Test precision validation with normal flags."""
    handler = TranscriptionHandler(Mock())
    
    fp16, fp32 = handler.validate_precision(fp16=True, fp32=False)
    
    assert fp16 is True
    assert fp32 is False
```

#### **Integration Tests**

```text
tests/integration/webui/
├── __init__.py
└── test_webui_integration.py
```

Example: `tests/integration/webui/test_webui_integration.py`

```python
"""Integration tests for WebUI."""

from __future__ import annotations

import pytest

from parakeet_rocm.webui.app import build_app


@pytest.mark.integration
def test_build_app_creates_gradio_blocks() -> None:
    """Test that build_app returns a Gradio Blocks instance."""
    app = build_app()
    
    # Import here to avoid loading Gradio in unit tests
    import gradio as gr
    
    assert isinstance(app, gr.Blocks)


@pytest.mark.integration
def test_app_has_required_components() -> None:
    """Test that app contains expected UI components."""
    app = build_app()
    
    # Check app has components
    # This is a basic smoke test
    assert app is not None
```

### Phase 6: Documentation (Day 5)

1. **Update README.md**

   ```markdown
   ## WebUI
   
   Launch the Gradio WebUI for a user-friendly interface:
   
   ```bash
   # Basic launch
   parakeet-rocm webui
   
   # Custom host and port
   parakeet-rocm webui --host 127.0.0.1 --port 7862
   
   # Enable public sharing (creates public URL)
   parakeet-rocm webui --share
   
   # Enable debug mode
   parakeet-rocm webui --debug
   ```

   The WebUI provides:
   - **Drag-and-drop file upload** for audio/video files
   - **Interactive configuration** with collapsible sections
   - **Quick presets** for common use cases
   - **Light/dark theme** with persistent preferences
   - **Real-time progress** and output file downloads

2. **Update project-overview.md**

   Add WebUI section:

   ```markdown
   ### WebUI Sub-module
   
   **Location**: `parakeet_rocm/webui/`
   
   The WebUI provides a browser-based interface built with Gradio.
   
   #### Architecture
   
   - **Modular Design**: Separated into UI, handlers, validation, and styling
   - **Protocol-Based**: Uses dependency injection for testability
   - **Lazy Loading**: Gradio imported only when WebUI is launched
   - **Theme Support**: Persistent light/dark mode via localStorage
   
   #### Components
   
   - `app.py`: Application builder and launcher
   - `handlers.py`: Business logic and transcription orchestration
   - `validation.py`: Input validation and error handling
   - `styles.py`: CSS and JavaScript for theming
   - `ui/layouts.py`: UI layout builders
   - `ui/presets.py`: Quick preset configurations
   - `ui/components.py`: Reusable UI components
   ```

3. **Add WebUI docstring documentation**

   Create comprehensive module docstrings following Google style.

### Phase 7: Cleanup (Day 5)

1. **Deprecate old script**

   Add deprecation notice to `scripts/parakeet_gradio_app.py`:

   ```python
   """DEPRECATED: Use `parakeet-rocm webui` instead.
   
   This script is maintained for backward compatibility but will be
   removed in v1.0.0. Please migrate to the new CLI command:
   
       parakeet-rocm webui
   
   See documentation for details.
   """
   ```

2. **Update VERSIONS.md**

   Add entry for v0.9.0 documenting the WebUI integration.

---

## Testing Strategy

### Unit Tests

- Mock all external dependencies
- Test each component in isolation
- Achieve >85% coverage per AGENTS.md

### Integration Tests

- Test WebUI app building
- Test handler integration with transcription
- Use markers: `@pytest.mark.integration`

### Manual Testing Checklist

- [ ] Launch WebUI via CLI
- [ ] Upload files and run transcription
- [ ] Test all presets
- [ ] Test theme switching
- [ ] Test error handling (invalid files, etc.)
- [ ] Test with different output formats
- [ ] Test precision flag conflicts
- [ ] Test on different browsers

---

## Dependencies

**Already satisfied**:

- `gradio>=5.39.0` in `webui` optional dependency group

**Installation**:

```bash
pdm install -G webui
```

---

## Backward Compatibility

- Old script `scripts/parakeet_gradio_app.py` remains functional
- Deprecation notice added
- Will be removed in v1.0.0
- Migration is straightforward: `python scripts/parakeet_gradio_app.py` → `parakeet-rocm webui`

---

## Success Criteria

- ✅ WebUI accessible via `parakeet-rocm webui` CLI command
- ✅ All functionality from old script preserved
- ✅ Modular, testable architecture
- ✅ Test coverage ≥85%
- ✅ Full documentation (README, project-overview, docstrings)
- ✅ Passes all Ruff checks (PEP8, docstrings, type hints)
- ✅ Environment variables properly configured
- ✅ No breaking changes to existing CLI

---

## Timeline

| Phase | Days | Focus | Status |
|-------|------|-------|--------|
| 1. Core Infrastructure | 5 | job_manager, session, validation, schemas | Pending |
| 2. UI Components | 5 | Components, pages, theme, presets | Pending |
| 3. Testing & Docs | 5 | Unit/integration tests, documentation | Pending |
| **Total** | **15 days** | **3 weeks for production-ready release** | |

---

## Future Enhancements

**Post v0.9.0**:

- [ ] Multi-language support in UI
- [ ] Real-time transcription preview
- [ ] Batch job queue management
- [ ] User authentication (optional)
- [ ] Persistent session storage
- [ ] Export settings as config file
- [ ] Advanced audio visualization
- [ ] Integration with watch mode

---

## References

- **Gradio Documentation**: <https://gradio.app/docs>
- **Project Coding Standards**: `AGENTS.md`
- **Test Suite Workflow**: `.windsurf/workflows/test-suite.md`
- **Architecture Overview**: `project-overview.md`

---

## Conclusion

This plan delivers a production-ready Gradio WebUI designed from the ground up with modern web app patterns and software engineering best practices.

### Design Highlights

✅ **Clean Architecture**: Layered design (presentation → business logic → validation → domain)  
✅ **SOLID Principles**: Protocol-oriented, dependency-injected, easily testable  
✅ **Modern UX**: Progressive disclosure, clear feedback, responsive  
✅ **Type-Safe**: Pydantic validation schemas throughout  
✅ **Maintainable**: Modular components, comprehensive tests, full documentation  

### Key Deliverables

1. **`parakeet_rocm/webui/` sub-module** with 9+ focused modules
2. **`parakeet-rocm webui` CLI command** for easy access
3. **Component library** for reusable UI elements
4. **Job management system** with full lifecycle tracking
5. **Comprehensive test suite** (unit + integration, >85% coverage)
6. **Complete documentation** (README, project-overview, inline docs)

### What Makes This Better Than POC

- **Not a refactor**: Fresh design from first principles
- **Extensible**: Easy to add features (async jobs, history, real-time updates)
- **Testable**: Proper dependency injection and protocols
- **Professional**: Production-ready error handling and validation
- **Maintainable**: Clear separation of concerns, well-documented

### Next Steps

1. **Review this plan** and provide feedback
2. **Start Phase 1**: Core infrastructure (job_manager, session, validation)
3. **Iterate rapidly**: Build, test, refine in 1-week sprints
4. **Ship v0.9.0**: Production-ready WebUI in 3 weeks
