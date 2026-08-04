"""Integration tests for the nvidia/parakeet-unified-en-0.6b model.

GPU-dependent tests are marked ``gpu`` and ``slow`` because they require a
ROCm/CUDA-capable device and a network model download. They skip cleanly when
those prerequisites are unavailable, so they can live in the suite without
breaking local or CI runs that lack GPU/model access. The non-GPU availability
test still runs in ordinary CI.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# Shared sample audio path used elsewhere in the integration suite.
AUDIO_PATH = Path(__file__).parents[2] / "data" / "samples" / "sample_mono.wav"

UNIFIED_MODEL_NAME = "nvidia/parakeet-unified-en-0.6b"

_IN_CI = os.getenv("CI") == "true"


def _gpu_available() -> bool:
    """Return whether a GPU usable by torch is present."""
    try:
        import torch
    except (ModuleNotFoundError, OSError, RuntimeError):
        return False
    try:
        return bool(torch.cuda.is_available())
    except (OSError, RuntimeError):
        return False


def _audio_skip() -> pytest.MarkDecorator:
    """Return a pytest skip mark for missing sample audio."""
    return pytest.mark.skipif(
        not AUDIO_PATH.is_file(),
        reason=f"sample audio not present at {AUDIO_PATH}",
    )


_GPU_SKIP = pytest.mark.skipif(
    not _gpu_available(),
    reason="GPU test skipped because torch reports no CUDA/ROCm device",
)
_AUDIO_SKIP = _audio_skip()
_CI_SKIP = pytest.mark.skipif(
    _IN_CI,
    reason="GPU tests are skipped in CI",
)


def _model_name_for_test() -> str:
    """Allow env override for the unified model under test.

    Returns:
        str: Model name to load during the test.
    """
    return os.getenv("PARAKEET_UNIFIED_MODEL_NAME", UNIFIED_MODEL_NAME)


@pytest.fixture(scope="module")
def loaded_unified_model() -> Iterator[Any]:
    """Load the unified model and guarantee cache cleanup on teardown.

    Yields:
        The loaded model object.
    """
    from parakeet_rocm.models.parakeet import clear_model_cache, get_model

    model_name = _model_name_for_test()
    clear_model_cache()
    try:
        model = get_model(model_name)
        yield model
    finally:
        clear_model_cache()


@pytest.fixture(scope="module")
def prepared_audio() -> Iterator[tuple[Any, list[tuple[Any, int]]]]:
    """Load sample audio and return the waveform plus segment list.

    Yields:
        Tuple of ``(wav, segments)``.
    """
    from parakeet_rocm.transcription.file_processor import load_and_prepare_audio

    wav, _sample_rate, segments, _load_elapsed, _duration = load_and_prepare_audio(
        audio_path=AUDIO_PATH,
        chunk_len_sec=30,
        overlap_duration=0,
        verbose=False,
        quiet=True,
    )
    yield wav, segments


@pytest.fixture(scope="module")
def aligned_result(
    loaded_unified_model: Any,
    prepared_audio: tuple[Any, list[tuple[Any, int]]],
) -> Any:
    """Transcribe the sample audio and adapt the hypotheses to word timestamps.

    Returns:
        The adapted alignment result.
    """
    from parakeet_rocm.timestamps.adapt import adapt_nemo_hypotheses
    from parakeet_rocm.transcription.utils import calc_time_stride

    wav, _segments = prepared_audio
    results = loaded_unified_model.transcribe(
        audio=[wav],
        batch_size=1,
        return_hypotheses=True,
        verbose=False,
    )
    hypotheses = results if isinstance(results, list) else [results[0]]
    for hyp in hypotheses:
        hyp.start_offset = 0.0
    time_stride = calc_time_stride(loaded_unified_model, verbose=False)
    return adapt_nemo_hypotheses(hypotheses, loaded_unified_model, time_stride)


@_CI_SKIP
@_GPU_SKIP
@_AUDIO_SKIP
@pytest.mark.gpu
@pytest.mark.slow
def test_get_model__loads_unified_model(loaded_unified_model: Any) -> None:
    """Verify the unified model can be loaded via the project's model accessor."""
    assert loaded_unified_model is not None
    assert hasattr(loaded_unified_model, "transcribe")


@_CI_SKIP
@_GPU_SKIP
@_AUDIO_SKIP
@pytest.mark.gpu
@pytest.mark.slow
def test_transcribe__returns_non_empty_plain_text_for_unified_model(
    loaded_unified_model: Any,
    prepared_audio: tuple[Any, list[tuple[Any, int]]],
) -> None:
    """Verify the unified model returns non-empty plain text on sample audio."""
    wav, _segments = prepared_audio
    results = loaded_unified_model.transcribe(
        audio=[wav],
        batch_size=1,
        return_hypotheses=False,
        verbose=False,
    )

    assert results
    text = results[0].text if hasattr(results[0], "text") else str(results[0])
    assert text.strip(), "unified model returned empty transcription"


@_CI_SKIP
@_GPU_SKIP
@_AUDIO_SKIP
@pytest.mark.gpu
@pytest.mark.slow
def test_adapt_nemo_hypotheses__does_not_crash_for_unified_model(
    aligned_result: Any,
) -> None:
    """Verify the unified model's hypotheses can be adapted to word timestamps."""
    assert aligned_result is not None
    # We do not require word timestamps; unified models may not expose them.
    # The important contract is that the adapter does not crash.


@_CI_SKIP
@_GPU_SKIP
@_AUDIO_SKIP
@pytest.mark.gpu
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["txt", "json", "jsonl", "csv", "tsv", "srt", "vtt"])
def test_output_formatter__renders_unified_model_result(
    fmt: str,
    tmp_path: Path,
    aligned_result: Any,
) -> None:
    """Verify every required output formatter accepts the unified model result."""
    from parakeet_rocm.formatting import FORMATTERS, get_formatter_spec

    assert fmt in FORMATTERS, f"requested format {fmt} is not registered"

    spec = get_formatter_spec(fmt)
    if spec.requires_word_timestamps and not aligned_result.word_segments:
        pytest.skip(f"unified model produced no word timestamps; format {fmt} cannot be tested")

    formatter = spec.format_func
    rendered = formatter(aligned_result)

    assert isinstance(rendered, str), f"formatter {fmt} returned {type(rendered)}, expected str"
    assert rendered.strip(), f"formatter {fmt} produced empty output"
    out_path = tmp_path / f"unified.{fmt}"
    out_path.write_text(rendered, encoding="utf-8")
    assert out_path.read_text(encoding="utf-8") == rendered


@pytest.mark.integration
def test_gpu_availability__reports_bool_without_torch_or_gpu() -> None:
    """Guard: ensure skip detection returns a boolean and does not raise."""
    available = _gpu_available()
    assert isinstance(available, bool)  # type: ignore[no-any-return]
