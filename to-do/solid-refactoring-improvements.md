# To-Do: SOLID Principles Refactoring and Improvements

This plan outlines the steps to refactor the codebase to achieve A-grade (90+) SOLID compliance by addressing identified violations in the comprehensive SOLID analysis. The focus is on breaking down large procedural functions, introducing configuration objects, and removing hard-coded type checks.

## Tasks

- [x] **Analysis Phase:**
  - [x] Complete SOLID principles analysis
    - Path: `to-do/solid-principles-analysis.md`
    - Action: Comprehensive evaluation of codebase against SOLID principles
    - Analysis Results:
      - Overall Grade: B+ (85/100)
      - Single Responsibility: 75/100 (large procedural functions)
      - Open/Closed: 90/100 (excellent formatter registry)
      - Liskov Substitution: 95/100 (strong protocol-based design)
      - Interface Segregation: 70/100 (parameter explosion issues)
      - Dependency Inversion: 95/100 (exemplary abstractions)
    - Accept Criteria: ✅ Analysis complete with prioritized recommendations

- [x] **Implementation Phase 1: Configuration Objects (HIGH Priority)**
  - [x] Create configuration dataclasses
    - Path: `parakeet_rocm/config.py` (new file)
    - Action: Define `TranscriptionConfig`, `StabilizationConfig`, `OutputConfig`, and `UIConfig` dataclasses
    - Implementation Details:

      ```python
      @dataclass
      class TranscriptionConfig:
          """Groups transcription-related settings."""
          batch_size: int = 12
          chunk_len_sec: int = 300
          overlap_duration: int = 15
          word_timestamps: bool = False
          merge_strategy: str = "lcs"
      
      @dataclass
      class StabilizationConfig:
          """Groups stable-ts settings."""
          enabled: bool = False
          demucs: bool = False
          vad: bool = False
          vad_threshold: float = 0.35
      
      @dataclass
      class OutputConfig:
          """Groups output-related settings."""
          output_dir: Path
          output_format: str
          output_template: str
          overwrite: bool = False
      
      @dataclass
      class UIConfig:
          """Groups UI/logging settings."""
          verbose: bool = False
          quiet: bool = False
          no_progress: bool = False
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ All config classes defined with proper type hints and docstrings
    - Note: Config defaults now use `DEFAULT_BATCH_SIZE` and `DEFAULT_CHUNK_LEN_SEC` from `utils/constant.py` to honor environment variable loading pattern
  
  - [x] Update `transcribe_file()` signature
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Replace 24 individual parameters with config objects
    - Implementation Details:

      ```python
      def transcribe_file(
          audio_path: Path,
          model: SupportsTranscribe,
          formatter: Formatter,
          file_idx: int,
          transcription_config: TranscriptionConfig,
          stabilization_config: StabilizationConfig,
          output_config: OutputConfig,
          ui_config: UIConfig,
          watch_base_dirs: Sequence[Path] | None = None,
          progress: Progress | None = None,
          main_task: TaskID | None = None,
      ) -> Path | None:
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ Function signature reduced from 24 to ~11 parameters
  
  - [x] Update `cli_transcribe()` signature
    - Path: `parakeet_rocm/transcription/cli.py`
    - Action: Update to use config objects
    - Status: ✅ Complete
    - Accept Criteria: ✅ CLI function uses config objects consistently
  
  - [x] Update CLI command to build config objects
    - Path: `parakeet_rocm/cli.py`
    - Action: Construct config objects from CLI arguments before calling transcription functions
    - Status: ✅ Complete
    - Accept Criteria: ✅ All CLI arguments properly mapped to config objects
  
  - [x] Update all call sites
    - Path: Multiple files in `parakeet_rocm/`
    - Action: Update all functions that call `transcribe_file()` to use new signature
    - Status: ✅ Complete
    - Accept Criteria: ✅ All call sites updated, no breaking changes
  
  - [x] Estimated Effort: 2-3 hours (Actual: ~2 hours)

- [ ] **Implementation Phase 2: Refactor `transcribe_file()` (HIGH Priority)**
  - [ ] Extract audio loading logic
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_load_and_prepare_audio()` function
    - Implementation Details:

      ```python
      def _load_and_prepare_audio(
          audio_path: Path,
          chunk_len_sec: int,
          verbose: bool,
      ) -> tuple[np.ndarray, int, list[tuple[int, int]]]:
          """Load audio file and prepare segments for transcription."""
          # Extract lines 230-260 from current transcribe_file()
      ```

    - Status: Pending
    - Accept Criteria: Audio loading isolated with clear inputs/outputs
  
  - [ ] Extract transcription orchestration
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_transcribe_segments()` function
    - Implementation Details:

      ```python
      def _transcribe_segments(
          model: SupportsTranscribe,
          audio: np.ndarray,
          sample_rate: int,
          segments: list[tuple[int, int]],
          config: TranscriptionConfig,
          ui_config: UIConfig,
          progress: Progress | None = None,
      ) -> list[Hypothesis]:
          """Transcribe audio segments and return hypotheses."""
          # Extract batch transcription logic (lines 280-350)
      ```

    - Status: Pending
    - Accept Criteria: Transcription logic isolated and testable
  
  - [ ] Extract timestamp merging logic
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_merge_timestamps()` function
    - Implementation Details:

      ```python
      def _merge_timestamps(
          hypotheses: list[Hypothesis],
          segments: list[tuple[int, int]],
          merge_strategy: str,
          overlap_duration: int,
      ) -> list[Word]:
          """Merge word timestamps from multiple segments."""
          # Extract merging logic (lines 360-400)
      ```

    - Status: Pending
    - Accept Criteria: Merging logic extracted with clear interface
  
  - [ ] Extract stabilization logic
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_apply_stabilization()` function
    - Implementation Details:

      ```python
      def _apply_stabilization(
          aligned_result: AlignedResult,
          audio_path: Path,
          config: StabilizationConfig,
          verbose: bool,
      ) -> AlignedResult:
          """Apply stable-ts refinement if enabled."""
          # Extract stabilization logic (lines 410-450)
      ```

    - Status: Pending
    - Accept Criteria: Stabilization isolated behind clear interface
  
  - [ ] Extract output formatting and saving
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_format_and_save_output()` function
    - Implementation Details:

      ```python
      def _format_and_save_output(
          aligned_result: AlignedResult,
          formatter: Formatter,
          output_config: OutputConfig,
          audio_path: Path,
          file_idx: int,
          watch_base_dirs: Sequence[Path] | None,
          verbose: bool,
      ) -> Path:
          """Format transcription and save to file."""
          # Extract output logic (lines 460-490)
      ```

    - Status: Pending
    - Accept Criteria: Output handling isolated and testable
  
  - [ ] Refactor main `transcribe_file()` to orchestrate
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Simplify main function to call extracted helpers
    - Implementation Details:

      ```python
      def transcribe_file(...) -> Path | None:
          """Transcribe audio file with word-level timestamps."""
          audio, sample_rate, segments = _load_and_prepare_audio(...)
          hypotheses = _transcribe_segments(...)
          words = _merge_timestamps(...)
          aligned_result = AlignedResult(words=words, segments=...)
          if stabilization_config.enabled:
              aligned_result = _apply_stabilization(...)
          return _format_and_save_output(...)
      ```

    - Status: Pending
    - Accept Criteria: Main function reduced to ~50 lines of orchestration
  
  - [ ] Estimated Effort: 4-6 hours

- [ ] **Implementation Phase 3: Formatter Metadata (MEDIUM Priority)**
  - [ ] Define `FormatterSpec` dataclass
    - Path: `parakeet_rocm/formatting/__init__.py`
    - Action: Create formatter metadata structure
    - Implementation Details:

      ```python
      @dataclass
      class FormatterSpec:
          """Metadata and function for a specific output format."""
          format_func: Callable[[AlignedResult], str]
          requires_word_timestamps: bool
          supports_highlighting: bool
          file_extension: str
      ```

    - Status: Pending
    - Accept Criteria: FormatterSpec defined with proper types
  
  - [ ] Update formatter registry
    - Path: `parakeet_rocm/formatting/__init__.py`
    - Action: Replace simple dict with FormatterSpec registry
    - Implementation Details:

      ```python
      FORMATTERS: Dict[str, FormatterSpec] = {
          "txt": FormatterSpec(to_txt, False, False, ".txt"),
          "srt": FormatterSpec(to_srt, True, True, ".srt"),
          "vtt": FormatterSpec(to_vtt, True, True, ".vtt"),
          "json": FormatterSpec(to_json, False, False, ".json"),
          # ... other formats
      }
      ```

    - Status: Pending
    - Accept Criteria: All formatters registered with metadata
  
  - [ ] Remove hard-coded format checks
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Replace `if output_format in ["txt", "json"]` with metadata queries
    - Implementation Details:

      ```python
      formatter_spec = FORMATTERS[output_format]
      if formatter_spec.requires_word_timestamps and not word_timestamps:
          # Error handling
      ```

    - Status: Pending
    - Accept Criteria: No hard-coded format lists in file_processor.py
  
  - [ ] Update all formatters to accept **kwargs
    - Path: `parakeet_rocm/formatting/_*.py`
    - Action: Ensure all formatters gracefully ignore unsupported parameters
    - Implementation Details:

      ```python
      def to_txt(result: AlignedResult, **kwargs) -> str:
          # Ignores highlight_words, etc.
      ```

    - Status: Pending
    - Accept Criteria: All formatters have uniform signatures
  
  - [ ] Estimated Effort: 1-2 hours

- [ ] **Implementation Phase 4: Merge Strategy Registry (LOW Priority)**
  - [ ] Create merge strategy registry
    - Path: `parakeet_rocm/chunking/merge.py`
    - Action: Add strategy dictionary
    - Implementation Details:

      ```python
      MERGE_STRATEGIES: Dict[str, Callable] = {
          "contiguous": merge_longest_contiguous,
          "lcs": merge_longest_common_subsequence,
      }
      ```

    - Status: Pending
    - Accept Criteria: Strategy registry defined and exported
  
  - [ ] Replace conditional with registry lookup
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Replace if/else with dictionary lookup
    - Implementation Details:

      ```python
      merger = MERGE_STRATEGIES[merge_strategy]
      merged_words = merger(merged_words, next_words, overlap_duration=...)
      ```

    - Status: Pending
    - Accept Criteria: No merge strategy conditionals in file_processor.py
  
  - [ ] Estimated Effort: 30 minutes

- [ ] **Implementation Phase 5: Refactor Large Functions (LOW-MEDIUM Priority)**
  - [ ] Refactor `segment_words()`
    - Path: `parakeet_rocm/timestamps/segmentation.py`
    - Action: Extract helper methods into `SegmentationPipeline` class
    - Status: Pending
    - Accept Criteria: Function broken into focused methods
  
  - [ ] Refactor `adapt_nemo_hypotheses()`
    - Path: `parakeet_rocm/timestamps/adapt.py`
    - Action: Extract merge passes into separate functions or `SegmentMerger` class
    - Status: Pending
    - Accept Criteria: Merge strategies isolated and testable
  
  - [ ] Extract watch mode setup from CLI
    - Path: `parakeet_rocm/cli.py`
    - Action: Move lines 335-392 to separate function
    - Status: Pending
    - Accept Criteria: Watch mode setup isolated
  
  - [ ] Estimated Effort: 3-4 hours

- [ ] **Testing Phase:**
  - [x] Unit tests for configuration objects
    - Path: `tests/test_config.py` (new file)
    - Action: Test config object creation, validation, and defaults
    - Accept Criteria: ✅ 100% coverage of config classes (11 tests passing)
  
  - [ ] Unit tests for extracted functions
    - Path: `tests/test_file_processor.py`
    - Action: Test each extracted helper function independently
    - Accept Criteria: All new functions have focused unit tests
  
  - [ ] Integration tests for refactored transcribe_file()
    - Path: `tests/integration/test_transcription_pipeline.py`
    - Action: Verify end-to-end transcription still works correctly
    - Accept Criteria: All existing integration tests pass
  
  - [ ] Tests for formatter metadata
    - Path: `tests/test_formatting.py`
    - Action: Test FormatterSpec registry and metadata queries
    - Accept Criteria: Formatter selection logic fully tested
  
  - [ ] Regression tests
    - Path: `tests/`
    - Action: Run full test suite to ensure no breaking changes
    - Accept Criteria: All existing tests pass, coverage ≥ 85%
  
  - [ ] Estimated Effort: 2-3 hours

- [ ] **Documentation Phase:**
  - [x] Update `project-overview.md`
    - Path: `project-overview.md`
    - Action: Document new configuration objects and refactored architecture
    - Accept Criteria: ✅ Architecture section reflects new design (added Section 3: Configuration Objects)
  
  - [ ] Update function docstrings
    - Path: Multiple files
    - Action: Ensure all new/modified functions have Google-style docstrings
    - Accept Criteria: All public functions properly documented
  
  - [ ] Update SOLID analysis report
    - Path: `to-do/solid-principles-analysis.md`
    - Action: Mark completed improvements and update scores
    - Accept Criteria: Report reflects post-refactoring state
  
  - [ ] Create migration guide
    - Path: `docs/migration-guide.md` (new file, optional)
    - Action: Document breaking changes for external users (if any)
    - Accept Criteria: Clear upgrade path documented

## Related Files

### Core Implementation Files

- `parakeet_rocm/config.py` (new)
- `parakeet_rocm/transcription/file_processor.py`
- `parakeet_rocm/transcription/cli.py`
- `parakeet_rocm/cli.py`
- `parakeet_rocm/formatting/__init__.py`
- `parakeet_rocm/formatting/_*.py`
- `parakeet_rocm/chunking/merge.py`
- `parakeet_rocm/timestamps/segmentation.py`
- `parakeet_rocm/timestamps/adapt.py`

### Test Files

- `tests/test_config.py` (new)
- `tests/test_file_processor.py`
- `tests/test_formatting.py`
- `tests/integration/test_transcription_pipeline.py`

### Documentation Files

- `project-overview.md`
- `to-do/solid-principles-analysis.md`
- `docs/migration-guide.md` (optional)

## Priority Order

1. **Phase 1: Configuration Objects** (HIGH) — 2-3 hours
   - Immediate impact on Interface Segregation violations
   - Foundation for other refactorings
   - Low risk, high value

2. **Phase 2: Refactor `transcribe_file()`** (HIGH) — 4-6 hours
   - Addresses Single Responsibility violations
   - Improves testability significantly
   - Requires careful extraction to avoid breaking changes

3. **Phase 3: Formatter Metadata** (MEDIUM) — 1-2 hours
   - Fixes Open/Closed violations
   - Makes adding new formats trivial
   - Low risk, clear benefit

4. **Phase 4: Merge Strategy Registry** (LOW) — 30 minutes
   - Minor Open/Closed improvement
   - Quick win, minimal effort

5. **Phase 5: Refactor Large Functions** (LOW-MEDIUM) — 3-4 hours
   - Further SRP improvements
   - Can be done incrementally
   - Lower priority than core refactorings

## Success Metrics

- **SOLID Score**: Increase from B+ (85/100) to A- (90+/100)
- **Code Coverage**: Maintain ≥ 85% line coverage
- **Function Complexity**: Reduce `transcribe_file()` from 320 lines to ~50 lines
- **Parameter Count**: Reduce from 24 parameters to ~11 parameters
- **Test Suite**: All existing tests pass, new tests added for extracted functions
- **CI/CD**: All linting and formatting checks pass

## Future Enhancements

- [ ] Consider `TranscriptionPipeline` class for even better encapsulation
- [ ] Explore dependency injection for file I/O (LOW severity DIP violation)
- [ ] Define local Protocol abstractions for NeMo types (MEDIUM severity DIP violation)
- [ ] Inject inference context manager for better testability (LOW severity DIP violation)
- [ ] Add performance benchmarks to ensure refactoring doesn't impact speed
- [ ] Create architectural decision records (ADRs) for major design choices

## Estimated Total Effort

**12-18 hours** spread across multiple PRs:

- PR 1: Configuration objects (2-3 hours + tests)
- PR 2: Refactor `transcribe_file()` (4-6 hours + tests)
- PR 3: Formatter metadata + merge registry (2 hours + tests)
- PR 4: Additional function refactorings (3-4 hours + tests)
- PR 5: Documentation updates (1-2 hours)

## Notes

- Each phase should be implemented in a separate PR for easier review
- Run full test suite after each phase to catch regressions early
- Update `VERSIONS.md` appropriately (likely a minor version bump for breaking API changes)
- Consider creating GitHub issues for each high-priority item
- Add integration tests before major refactorings to ensure behavior preservation
