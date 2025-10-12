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

- [x] **Implementation Phase 2: Refactor `transcribe_file()` (HIGH Priority)**
  - [x] Extract audio loading logic
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_load_and_prepare_audio()` function
    - Implementation Details:

      ```python
      def _load_and_prepare_audio(
          audio_path: Path,
          chunk_len_sec: int,
          overlap_duration: int,
          verbose: bool,
          quiet: bool,
      ) -> tuple[Any, int, list[tuple[Any, int]], float, float]:
          """Load audio file and prepare segments for transcription."""
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ Audio loading isolated with clear inputs/outputs (lines 194-238)
  
  - [x] Extract transcription orchestration
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Use existing `_transcribe_batches()` function
    - Status: ✅ Complete (already existed, lines 87-140)
    - Accept Criteria: ✅ Transcription logic isolated and testable
  
  - [x] Extract timestamp merging logic
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Use existing `_merge_word_segments()` function
    - Status: ✅ Complete (already existed, lines 143-191)
    - Accept Criteria: ✅ Merging logic extracted with clear interface
  
  - [x] Extract stabilization logic
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_apply_stabilization()` function
    - Implementation Details:

      ```python
      def _apply_stabilization(
          aligned_result: AlignedResult,
          audio_path: Path,
          stabilization_config: StabilizationConfig,
          ui_config: UIConfig,
      ) -> AlignedResult:
          """Apply stable-ts refinement if enabled."""
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ Stabilization isolated behind clear interface (lines 241-388)
  
  - [x] Extract output formatting and saving
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Create `_format_and_save_output()` function
    - Implementation Details:

      ```python
      def _format_and_save_output(
          aligned_result: AlignedResult,
          formatter: Formatter | Callable[[AlignedResult], str],
          output_config: OutputConfig,
          audio_path: Path,
          file_idx: int,
          watch_base_dirs: Sequence[Path] | None,
          ui_config: UIConfig,
      ) -> Path:
          """Format transcription and save to file."""
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ Output handling isolated and testable (lines 391-474)
  
  - [x] Refactor main `transcribe_file()` to orchestrate
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Simplify main function to call extracted helpers
    - Implementation Details:

      ```python
      def transcribe_file(...) -> Path | None:
          """Transcribe audio file with word-level timestamps."""
          # Step 1: Load and prepare audio
          wav, sample_rate, segments, load_elapsed, duration_sec = _load_and_prepare_audio(...)
          
          # Step 2: Transcribe audio segments
          hypotheses, texts = _transcribe_batches(...)
          
          # Step 3: Process transcription results
          aligned_result = _merge_word_segments(...)
          aligned_result = _apply_stabilization(...)
          
          # Step 4: Format and save output
          return _format_and_save_output(...)
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ Main function reduced from 320 lines to ~155 lines of orchestration (lines 477-631)
  
  - [x] Estimated Effort: 4-6 hours (Actual: ~3 hours)

- [x] **Implementation Phase 3: Formatter Metadata (MEDIUM Priority)**
  - [x] Define `FormatterSpec` dataclass
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

    - Status: ✅ Complete
    - Accept Criteria: ✅ FormatterSpec defined with proper types (lines 23-38)
  
  - [x] Update formatter registry
    - Path: `parakeet_rocm/formatting/__init__.py`
    - Action: Replace simple dict with FormatterSpec registry
    - Implementation Details:

      ```python
      FORMATTERS: dict[str, FormatterSpec] = {
          "txt": FormatterSpec(to_txt, False, False, ".txt"),
          "srt": FormatterSpec(to_srt, True, True, ".srt"),
          "vtt": FormatterSpec(to_vtt, True, True, ".vtt"),
          "json": FormatterSpec(to_json, False, False, ".json"),
          # ... other formats (csv, tsv, jsonl)
      }
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ All 7 formatters registered with metadata (lines 42-85)
  
  - [x] Remove hard-coded format checks
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Replace `if output_format in ["txt", "json"]` with metadata queries
    - Implementation Details:

      ```python
      formatter_spec = get_formatter_spec(output_format)
      if formatter_spec.requires_word_timestamps and not word_timestamps:
          # Error handling
      if formatter_spec.supports_highlighting:
          formatter(result, highlight_words=True)
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ No hard-coded format lists in file_processor.py
  
  - [x] Update all formatters to accept **kwargs
    - Path: `parakeet_rocm/formatting/_*.py`
    - Action: Ensure all formatters gracefully ignore unsupported parameters
    - Implementation Details:

      ```python
      def to_txt(result: AlignedResult, **kwargs: object) -> str:
          # Ignores highlight_words, etc.
      ```

    - Status: ✅ Complete
    - Accept Criteria: ✅ All 7 formatters have uniform signatures with **kwargs
  
  - [x] Estimated Effort: 1-2 hours (Actual: ~1.5 hours)

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
  
  - [x] Unit tests for extracted functions
    - Path: `tests/test_file_processor.py` (new file)
    - Action: Test each extracted helper function independently
    - Accept Criteria: ✅ All new functions have focused unit tests (10 tests passing)
    - Tests Added:
      - `test_load_and_prepare_audio_basic()` - Basic audio loading
      - `test_load_and_prepare_audio_verbose()` - Verbose logging
      - `test_apply_stabilization_disabled()` - Stabilization disabled
      - `test_apply_stabilization_enabled()` - Stabilization enabled
      - `test_apply_stabilization_runtime_error()` - Error handling
      - `test_format_and_save_output_basic()` - Basic output
      - `test_format_and_save_output_with_highlight()` - SRT/VTT highlighting
      - `test_format_and_save_output_with_template()` - Template substitution
      - `test_format_and_save_output_subdirectory_mirroring()` - Watch mode
      - `test_format_and_save_output_overwrite_disabled()` - Unique filenames
  
  - [x] Integration tests for refactored transcribe_file()
    - Path: Existing integration tests
    - Action: Verify end-to-end transcription still works correctly
    - Accept Criteria: ✅ All existing integration tests pass (91 total tests passing)
  
  - [x] Tests for formatter metadata
    - Path: `tests/test_formatting.py` (new file)
    - Action: Test FormatterSpec registry and metadata queries
    - Accept Criteria: ✅ Formatter selection logic fully tested (17 tests passing)
    - Tests Added:
      - `test_formatter_spec_creation()` - FormatterSpec instantiation
      - `test_formatter_spec_defaults()` - Default values
      - `test_formatters_registry_contains_all_formats()` - Registry completeness
      - `test_all_formatters_are_formatter_specs()` - Type validation
      - `test_srt_formatter_spec_metadata()` - SRT metadata
      - `test_vtt_formatter_spec_metadata()` - VTT metadata
      - `test_txt_formatter_spec_metadata()` - TXT metadata
      - `test_json_formatter_spec_metadata()` - JSON metadata
      - `test_get_formatter_returns_callable()` - Formatter retrieval
      - `test_get_formatter_case_insensitive()` - Case handling
      - `test_get_formatter_raises_on_unknown_format()` - Error handling
      - `test_get_formatter_spec_returns_spec()` - Spec retrieval
      - `test_get_formatter_spec_case_insensitive()` - Spec case handling
      - `test_get_formatter_spec_raises_on_unknown_format()` - Spec error handling
      - `test_txt_formatter_ignores_highlight_words()` - **kwargs support
      - `test_json_formatter_ignores_highlight_words()` - **kwargs support
      - `test_srt_formatter_accepts_highlight_words()` - Highlighting support
    - Status: ✅ Complete
  
  - [x] Regression tests
    - Path: `tests/`
    - Action: Run full test suite to ensure no breaking changes
    - Accept Criteria: ✅ All tests pass (108 passed, 3 skipped), coverage maintained
    - Phase 2: 91 tests passing
    - Phase 3: 108 tests passing (+17 formatter tests)
  
  - [x] Estimated Effort: 2-3 hours (Actual: ~2 hours)

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
