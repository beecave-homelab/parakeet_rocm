# WebUI UX Improvement Plan

**Status**: Draft  
**Created**: 2025-01-17  
**Priority**: High  
**Estimated Effort**: 3-5 days

---

## Executive Summary

The current WebUI implementation exposes only a **subset** of the CLI transcription pipeline's capabilities. This document identifies missing features, proposes a phased implementation plan, and ensures adherence to SOLID principles and the project's coding standards defined in `AGENTS.md`.

---

## 1. Feature Gap Analysis

### 1.0 Environment Variable Support

**Features with env-var/constant support** (already configurable via `.env`):

- ✅ `batch_size` → `DEFAULT_BATCH_SIZE` (default: 12)
- ✅ `chunk_len_sec` → `DEFAULT_CHUNK_LEN_SEC` (default: 300)
- ✅ `word_timestamps` → `DEFAULT_WORD_TIMESTAMPS` (default: False)
- ✅ `stabilize` → `DEFAULT_STABILIZE` (default: False)
- ✅ `vad` → `DEFAULT_VAD` (default: False)
- ✅ `demucs` → `DEFAULT_DEMUCS` (default: False)
- ✅ `stream_chunk_sec` → `DEFAULT_STREAM_CHUNK_SEC` (default: 8)

**Missing features with CLI hardcoded defaults** (not env-configurable):

- ❌ `overlap_duration` → hardcoded to `15` seconds in CLI
- ❌ `merge_strategy` → hardcoded to `"lcs"` in CLI
- ❌ `vad_threshold` → hardcoded to `0.35` in CLI
- ❌ `highlight_words` → hardcoded to `False` in CLI
- ❌ `overwrite` → hardcoded to `False` in CLI
- ❌ `output_template` → hardcoded to `"{filename}"` in CLI
- ❌ `stream` → hardcoded to `False` in CLI
- ❌ `verbose` → hardcoded to `False` in CLI

**Design Decision**: The `default` preset should mirror CLI defaults exactly (using constants where available, hardcoded values otherwise). Other presets can override these values when it makes sense for the use case.

### 1.1 Currently Implemented in WebUI

✅ **Core Features**:

- File upload (multiple audio/video files)
- Preset configurations (default, fast, balanced, high_quality, best)
- Basic transcription settings:
  - `batch_size` (1-32)
  - `chunk_len_sec` (30-600s)
  - `word_timestamps` (boolean)
  - `stabilize` (boolean, stable-ts)
  - `vad` (boolean, Voice Activity Detection)
  - `demucs` (boolean, Audio Enhancement)
  - `output_format` (txt, srt, vtt, json)
- Progress tracking with real-time updates
- Bulk download (ZIP for multiple files)
- Session management

### 1.2 Missing CLI Features

❌ **Critical Missing Features**:

#### A. Advanced Chunking & Streaming

| CLI Flag | Description | Current WebUI | Priority |
|----------|-------------|---------------|----------|
| `--overlap-duration` | Overlap between chunks (seconds) | ❌ Not exposed | **HIGH** |
| `--stream` | Enable pseudo-streaming mode | ❌ Not exposed | **MEDIUM** |
| `--stream-chunk-sec` | Streaming chunk size | ❌ Not exposed | **MEDIUM** |
| `--merge-strategy` | Chunk merge strategy (none/contiguous/lcs) | ❌ Not exposed | **HIGH** |

#### B. Timestamp & Subtitle Refinement

| CLI Flag | Description | Current WebUI | Priority |
|----------|-------------|---------------|----------|
| `--vad-threshold` | VAD probability threshold (0.0-1.0) | ❌ Not exposed (hardcoded 0.35) | **HIGH** |
| `--highlight-words` | Highlight words in SRT/VTT | ❌ Not exposed | **MEDIUM** |

#### C. Output Control

| CLI Flag | Description | Current WebUI | Priority |
|----------|-------------|---------------|----------|
| `--output-template` | Filename template ({filename}, {index}, {date}, {parent}) | ❌ Not exposed (hardcoded `{filename}`) | **LOW** |
| `--overwrite` | Overwrite existing files | ❌ Not exposed (hardcoded False) | **MEDIUM** |

#### D. Model & Performance

| CLI Flag | Description | Current WebUI | Priority |
|----------|-------------|---------------|----------|
| `--model` | Custom model path/HF ID | ❌ Not exposed (hardcoded to `PARAKEET_MODEL_NAME`) | **LOW** |
| `--fp16` / `--fp32` | Precision control | ✅ Partially (fp16 in presets, no UI toggle) | **MEDIUM** |

#### E. Logging & Diagnostics

| CLI Flag | Description | Current WebUI | Priority |
|----------|-------------|---------------|----------|
| `--verbose` | Enable verbose logging | ❌ Not exposed | **LOW** |
| `--quiet` | Suppress non-error output | ❌ Not exposed | **LOW** |
| `--no-progress` | Disable progress bars | ❌ Not exposed (N/A for WebUI) | **N/A** |

#### F. Watch Mode

| CLI Flag | Description | Current WebUI | Priority |
|----------|-------------|---------------|----------|
| `--watch` | Monitor directory for new files | ❌ Not exposed | **LOW** (WebUI-specific feature) |

---

## 2. Proposed Implementation Plan

### Phase 1: High-Priority Features (Week 1)

#### 1.1 Add Advanced Chunking Controls

**Files to modify**:

- `parakeet_rocm/webui/validation/schemas.py` - Add fields to `TranscriptionConfig`
- `parakeet_rocm/webui/app.py` - Add UI components
- `parakeet_rocm/webui/utils/presets.py` - Update preset definitions

**New UI Components**:

```python
# In Advanced Settings accordion
overlap_duration = gr.Slider(
    minimum=0,
    maximum=60,
    value=15,
    step=5,
    label="Overlap Duration (seconds)",
    info="Overlap between consecutive chunks for better continuity"
)

merge_strategy = gr.Dropdown(
    choices=["lcs", "contiguous", "none"],
    value="lcs",
    label="Merge Strategy",
    info="lcs=accurate (default), contiguous=fast, none=concatenate"
)
```

**Schema Changes**:

```python
# parakeet_rocm/webui/validation/schemas.py
class TranscriptionConfig(BaseModel):
    # ... existing fields ...
    overlap_duration: int = Field(
        default=15,
        ge=0,
        le=60,
        description="Overlap between chunks in seconds"
    )
    merge_strategy: Literal["lcs", "contiguous", "none"] = Field(
        default="lcs",
        description="Strategy for merging overlapping chunks"
    )
```

**Preset Updates**:

```python
# parakeet_rocm/webui/utils/presets.py
"fast": Preset(
    # ... existing config ...
    config=TranscriptionConfig(
        # ... existing fields ...
        overlap_duration=10,  # Shorter overlap for speed
        merge_strategy="contiguous",  # Fast merge
    ),
),
```

#### 1.2 Expose VAD Threshold Control

**New UI Component**:

```python
vad_threshold = gr.Slider(
    minimum=0.0,
    maximum=1.0,
    value=0.35,
    step=0.05,
    label="VAD Threshold",
    info="Voice activity detection sensitivity (higher = stricter)",
    visible=False,  # Show only when VAD is enabled
)

# Dynamic visibility
vad.change(
    fn=lambda enabled: gr.update(visible=enabled),
    inputs=[vad],
    outputs=[vad_threshold]
)
```

**Schema Update**:

```python
# Already exists in schemas.py, just needs UI exposure
vad_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
```

---

### Phase 2: Medium-Priority Features (Week 2)

#### 2.1 Add Streaming Mode Support

**New UI Components**:

```python
with gr.Row():
    stream_mode = gr.Checkbox(
        label="Streaming Mode",
        value=False,
        info="Enable low-latency pseudo-streaming (smaller chunks)"
    )
    stream_chunk_sec = gr.Slider(
        minimum=5,
        maximum=30,
        value=8,
        step=1,
        label="Stream Chunk Size (seconds)",
        visible=False,
    )

# Dynamic visibility and validation
stream_mode.change(
    fn=lambda enabled: gr.update(visible=enabled),
    inputs=[stream_mode],
    outputs=[stream_chunk_sec]
)
```

**Schema Changes**:

```python
class TranscriptionConfig(BaseModel):
    # ... existing fields ...
    stream: bool = Field(default=False, description="Enable streaming mode")
    stream_chunk_sec: int = Field(
        default=8,
        ge=5,
        le=30,
        description="Chunk size for streaming mode"
    )
```

#### 2.2 Add Highlight Words & Overwrite Options

**New UI Components**:

```python
with gr.Row():
    highlight_words = gr.Checkbox(
        label="Highlight Words (SRT/VTT)",
        value=False,
        info="Bold each word in subtitle outputs"
    )
    overwrite_files = gr.Checkbox(
        label="Overwrite Existing Files",
        value=False,
        info="Replace existing outputs instead of creating numbered copies"
    )
```

**Schema Changes**:

```python
class TranscriptionConfig(BaseModel):
    # ... existing fields ...
    highlight_words: bool = Field(default=False)
    overwrite: bool = Field(default=False)
```

#### 2.3 Add Precision Control Toggle

**New UI Component**:

```python
precision = gr.Radio(
    choices=["fp16", "fp32"],
    value="fp16",
    label="Inference Precision",
    info="fp16=faster (default), fp32=more accurate"
)
```

**Schema Update** (already exists, needs UI mapping):

```python
# Map radio selection to boolean flags
def map_precision(precision_choice):
    return {
        "fp16": precision_choice == "fp16",
        "fp32": precision_choice == "fp32"
    }
```

---

### Phase 3: Low-Priority & Polish (Week 3)

#### 3.1 Add Output Template Control

**New UI Component**:

```python
output_template = gr.Textbox(
    value="{filename}",
    label="Output Filename Template",
    info="Placeholders: {filename}, {index}, {date}, {parent}",
    placeholder="{filename}_{date}"
)
```

**Schema Update**:

```python
class TranscriptionConfig(BaseModel):
    # ... existing fields ...
    output_template: str = Field(
        default="{filename}",
        description="Filename template with placeholders"
    )
```

#### 3.2 Add Model Selection (Advanced Users)

**New UI Component**:

```python
with gr.Accordion("Expert Settings", open=False):
    model_name = gr.Textbox(
        value=PARAKEET_MODEL_NAME,
        label="Model Name or Path",
        info="HuggingFace model ID or local path (advanced users only)"
    )
```

**Schema Update** (already exists):

```python
model_name: str = Field(default=PARAKEET_MODEL_NAME)
```

#### 3.3 Add Verbose Logging Toggle

**New UI Component**:

```python
verbose_logging = gr.Checkbox(
    label="Verbose Logging",
    value=False,
    info="Show detailed diagnostics in console (for debugging)"
)
```

**Backend Integration**:

- Pass `verbose` flag to `cli_transcribe()`
- Display verbose output in a collapsible log viewer (optional)

---

## 3. UI/UX Design Recommendations

### 3.1 Reorganize Advanced Settings

**Current Structure**:

```txt
Advanced Settings (Accordion)
├── Batch Size
├── Chunk Length
├── Word Timestamps
├── Stabilize
├── VAD
├── Demucs
└── Output Format
```

**Proposed Structure**:

```txt
Advanced Settings (Accordion)
├── Performance (Tab)
│   ├── Batch Size
│   ├── Precision (fp16/fp32)
│   └── Streaming Mode
│       └── Stream Chunk Size (conditional)
├── Chunking (Tab)
│   ├── Chunk Length
│   ├── Overlap Duration
│   └── Merge Strategy
├── Timestamps (Tab)
│   ├── Word Timestamps
│   ├── Stabilize
│   ├── VAD
│   │   └── VAD Threshold (conditional)
│   ├── Demucs
│   └── Highlight Words
└── Output (Tab)
    ├── Output Format
    ├── Output Template
    └── Overwrite Files

Expert Settings (Accordion, collapsed by default)
├── Model Name/Path
└── Verbose Logging
```

### 3.2 Preset Enhancements

**Update Preset Descriptions**:

- Add tooltips showing which advanced settings each preset enables
- Display preset details in a collapsible info box

**New Preset Suggestions**:

```python
"streaming": Preset(
    name="streaming",
    description="Low-latency streaming mode for real-time-like processing",
    config=TranscriptionConfig(
        batch_size=8,
        chunk_len_sec=8,  # Overridden by stream_chunk_sec when stream=True
        stream=True,  # Enable streaming mode
        stream_chunk_sec=8,  # Small chunks for low latency
        overlap_duration=2,  # Minimal overlap for speed
        merge_strategy="contiguous",  # Fast merge
        word_timestamps=False,  # Disable for speed
        stabilize=False,
        vad=False,
        demucs=False,
        vad_threshold=0.35,  # Keep default (not used)
        highlight_words=False,
        overwrite=False,
        fp16=True,
    ),
),
"ultra_quality": Preset(
    name="ultra_quality",
    description="Maximum quality with all refinements and fp32 precision",
    config=TranscriptionConfig(
        batch_size=2,  # Smallest batch for maximum accuracy
        chunk_len_sec=150,
        overlap_duration=25,  # Maximum overlap for seamless transitions
        merge_strategy="lcs",  # Most accurate merge
        word_timestamps=True,
        stabilize=True,
        vad=True,
        vad_threshold=0.30,  # Lower threshold for more aggressive VAD
        demucs=True,
        highlight_words=True,  # Enable word highlighting
        overwrite=False,
        stream=False,
        stream_chunk_sec=DEFAULT_STREAM_CHUNK_SEC,
        fp32=True,  # Maximum precision (slower)
    ),
),
```

### 3.3 Conditional UI Elements

**Dynamic Visibility Rules**:

- Show `vad_threshold` only when `vad=True`
- Show `stream_chunk_sec` only when `stream=True`
- Show `highlight_words` only when `output_format` is `srt` or `vtt`
- Disable `stabilize` when `word_timestamps=False` (with warning tooltip)

---

## 4. Implementation Checklist

### 4.1 Code Changes

#### Phase 1 (High Priority)

- [ ] **Optional**: Add env-var support for missing features in `parakeet_rocm/utils/constant.py`:
  - [ ] Add `DEFAULT_OVERLAP_DURATION` (default: 15)
  - [ ] Add `DEFAULT_MERGE_STRATEGY` (default: "lcs")
  - [ ] Add `DEFAULT_VAD_THRESHOLD` (default: 0.35)
  - [ ] Add `DEFAULT_HIGHLIGHT_WORDS` (default: False)
  - [ ] Add `DEFAULT_OVERWRITE` (default: False)
  - [ ] Document new variables in `.env.example`
  - [ ] **Note**: This is optional; can use hardcoded defaults if env-var support not needed
- [ ] Update `parakeet_rocm/webui/validation/schemas.py`:
  - [ ] Add `overlap_duration` field (default: 15 or `DEFAULT_OVERLAP_DURATION` if added)
  - [ ] Add `merge_strategy` field (default: "lcs" or `DEFAULT_MERGE_STRATEGY` if added)
  - [ ] Expose `vad_threshold` in UI (already exists, default: 0.35)
- [ ] Update `parakeet_rocm/webui/app.py`:
  - [ ] Add `overlap_duration` slider
  - [ ] Add `merge_strategy` dropdown
  - [ ] Add `vad_threshold` slider with conditional visibility
  - [ ] Update `transcribe_files()` to pass new parameters
  - [ ] Update `apply_preset()` to include new fields
- [ ] Update `parakeet_rocm/webui/utils/presets.py`:
  - [ ] Add new fields to all preset configs
- [ ] Update `parakeet_rocm/webui/core/job_manager.py`:
  - [ ] Ensure `run_job()` passes all config fields to `cli_transcribe()`

#### Phase 2 (Medium Priority)

- [ ] Add streaming mode support (schema + UI)
- [ ] Add `highlight_words` checkbox
- [ ] Add `overwrite` checkbox
- [ ] Add precision radio button (fp16/fp32)
- [ ] Update presets with new fields

#### Phase 3 (Low Priority)

- [ ] Add `output_template` textbox
- [ ] Add `model_name` textbox in Expert Settings
- [ ] Add `verbose` logging toggle
- [ ] Reorganize UI into tabbed Advanced Settings
- [ ] Add new presets (streaming, ultra_quality)

### 4.2 Testing Requirements

#### Unit Tests

- [ ] `tests/unit/webui/test_schemas.py`:
  - [ ] Test new `TranscriptionConfig` fields
  - [ ] Test field validation (ranges, types)
  - [ ] Test precision flag mutual exclusion
- [ ] `tests/unit/webui/test_presets.py`:
  - [ ] Test updated preset configurations
  - [ ] Test new presets (streaming, ultra_quality)

#### Integration Tests

- [ ] `tests/integration/test_webui_app.py`:
  - [ ] Test UI component creation
  - [ ] Test preset application with new fields
  - [ ] Test conditional visibility logic
  - [ ] Test parameter passing to `cli_transcribe()`

#### E2E Tests

- [ ] `tests/e2e/test_webui_transcription.py`:
  - [ ] Test transcription with custom `overlap_duration`
  - [ ] Test transcription with different `merge_strategy` values
  - [ ] Test transcription with custom `vad_threshold`
  - [ ] Test streaming mode end-to-end
  - [ ] Test `highlight_words` in SRT output

### 4.3 Documentation Updates

- [ ] Update `project-overview.md`:
  - [ ] Document new WebUI features
  - [ ] Update feature parity table (CLI vs WebUI)
- [ ] Update `README.md`:
  - [ ] Add screenshots of new UI (if applicable)
  - [ ] Document new presets
- [ ] Create `docs/WEBUI_GUIDE.md`:
  - [ ] User guide for advanced settings
  - [ ] Preset comparison table
  - [ ] Troubleshooting section

---

## 5. SOLID Principles Compliance

### 5.1 Single Responsibility Principle (SRP)

✅ **Adherence**:

- `TranscriptionConfig` schema handles validation only
- `Preset` dataclass encapsulates preset definitions
- `JobManager` handles job lifecycle, not UI logic
- UI components in `app.py` delegate to core services

### 5.2 Open/Closed Principle (OCP)

✅ **Adherence**:

- New fields added to `TranscriptionConfig` without modifying existing validation logic
- Presets extended via dictionary, not hardcoded conditionals
- UI components added without breaking existing event handlers

### 5.3 Liskov Substitution Principle (LSP)

✅ **Adherence**:

- `TranscriptionConfig` maintains backward compatibility (new fields have defaults)
- Presets remain substitutable (all return same `Preset` type)

### 5.4 Interface Segregation Principle (ISP)

✅ **Adherence**:

- Config split into logical groups (already exists: `TranscriptionConfig`, `StabilizationConfig`, `OutputConfig`, `UIConfig`)
- WebUI schema mirrors CLI config structure
- No "fat interfaces" forcing unused parameters

### 5.5 Dependency Inversion Principle (DIP)

✅ **Adherence**:

- `JobManager` injected into `build_app()` (testable)
- `cli_transcribe()` called via abstraction, not direct import in UI logic
- Validation schemas decoupled from UI components

---

## 6. Risk Assessment

### 6.1 Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| UI becomes cluttered with too many options | High | Medium | Use tabbed interface + collapsible sections |
| Breaking changes to existing presets | Medium | Low | Add new fields with sensible defaults |
| Performance degradation with streaming mode | Medium | Low | Document trade-offs, add preset for streaming |
| Validation errors with new fields | Low | Medium | Comprehensive unit tests for schema validation |

### 6.2 UX Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Users overwhelmed by advanced options | High | High | Keep defaults sensible, hide expert settings |
| Preset selection confusion | Medium | Medium | Add tooltips + info boxes explaining presets |
| Conditional UI elements confusing | Medium | Low | Use clear labels + info text for dependencies |

---

## 7. Success Metrics

### 7.1 Feature Parity

- [ ] **Target**: 90%+ CLI feature coverage in WebUI
- [ ] **Current**: ~60% (8/14 major CLI flags exposed)
- [ ] **After Phase 1**: ~80% (11/14 flags)
- [ ] **After Phase 2**: ~90% (13/14 flags)

### 7.2 Code Quality

- [ ] All new code passes `ruff check` and `ruff format`
- [ ] Test coverage ≥85% for new modules
- [ ] Zero regressions in existing tests
- [ ] All docstrings follow Google style

### 7.3 User Experience

- [ ] Advanced settings remain collapsed by default
- [ ] Preset application updates all relevant UI fields
- [ ] Conditional visibility works without page refresh
- [ ] No performance degradation in UI responsiveness

---

## 8. Timeline & Effort Estimation

| Phase | Tasks | Estimated Effort | Dependencies |
|-------|-------|------------------|--------------|
| **Phase 1** | Overlap, merge strategy, VAD threshold | 1.5 days | None |
| **Phase 2** | Streaming, highlight, overwrite, precision | 1.5 days | Phase 1 |
| **Phase 3** | Output template, model selection, verbose, UI refactor | 2 days | Phase 2 |
| **Testing** | Unit + integration + E2E tests | 1 day | All phases |
| **Documentation** | Update docs, screenshots, guides | 0.5 days | All phases |
| **Total** | | **6.5 days** | |

**Buffer**: +20% for unexpected issues = **~8 days total**

---

## 9. Next Steps

### Immediate Actions

1. **Review & Approve Plan**: Stakeholder sign-off on proposed changes
2. **Create Feature Branch**: `git checkout -b feature/webui-ux-improvements`
3. **Phase 1 Implementation**: Start with high-priority features
4. **Iterative Testing**: Run tests after each phase completion

### Long-Term Considerations

- **User Feedback Loop**: Collect feedback on new UI after Phase 1
- **Performance Monitoring**: Track transcription times with new settings
- **Accessibility Audit**: Ensure UI remains accessible (ARIA labels, keyboard navigation)
- **Mobile Responsiveness**: Test on smaller screens (tablets, phones)

---

## 10. References

### Related Files

- `parakeet_rocm/cli.py` - CLI argument definitions
- `parakeet_rocm/transcription/cli.py` - Core transcription logic
- `parakeet_rocm/config.py` - Configuration dataclasses
- `parakeet_rocm/webui/app.py` - WebUI application
- `parakeet_rocm/webui/validation/schemas.py` - Pydantic schemas
- `parakeet_rocm/webui/utils/presets.py` - Preset definitions
- `AGENTS.md` - Coding standards and SOLID principles

### External Resources

- [Gradio Documentation](https://www.gradio.app/docs/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)

---

---

## 11. Key Findings Summary

### Environment Variable vs Hardcoded Defaults

**Investigation Results**:

- **7 features** already have env-var support via `utils/constant.py`:
  - `batch_size`, `chunk_len_sec`, `word_timestamps`, `stabilize`, `vad`, `demucs`, `stream_chunk_sec`
- **8 features** use CLI hardcoded defaults (no env-var support):
  - `overlap_duration=15`, `merge_strategy="lcs"`, `vad_threshold=0.35`, `highlight_words=False`, `overwrite=False`, `output_template="{filename}"`, `stream=False`, `verbose=False`

### Design Decision

**The `default` preset must mirror CLI defaults exactly**:

- Use `DEFAULT_*` constants where available (already implemented)
- Use CLI hardcoded values for features without env-var support
- Other presets (`fast`, `balanced`, `high_quality`, `best`) can override these values strategically based on their use case

**Optional Enhancement**:

- Add env-var support for remaining features by creating new constants in `utils/constant.py`
- This would allow users to customize defaults via `.env` file
- Not required for Phase 1, can be added later if needed

### Updated Preset Strategy

| Preset | `overlap_duration` | `merge_strategy` | `vad_threshold` | Rationale |
|--------|-------------------|------------------|-----------------|-----------|
| **default** | 15 (CLI default) | "lcs" (CLI default) | 0.35 (CLI default) | Mirrors CLI exactly |
| **fast** | 10 | "contiguous" | 0.35 | Shorter overlap + faster merge for speed |
| **balanced** | 15 | "lcs" | 0.35 | Standard settings |
| **high_quality** | 20 | "lcs" | 0.35 | Longer overlap for better continuity |
| **best** | 20 | "lcs" | 0.30 | Longer overlap + more aggressive VAD |
| **streaming** (new) | 2 | "contiguous" | 0.35 | Minimal overlap for low latency |
| **ultra_quality** (new) | 25 | "lcs" | 0.30 | Maximum overlap + aggressive VAD |

---

**Document Version**: 1.1  
**Last Updated**: 2025-01-17  
**Author**: AI Assistant  
**Status**: Ready for Review  
**Changelog**:

- v1.1: Added environment variable analysis, clarified `default` preset must use CLI defaults
- v1.0: Initial plan
