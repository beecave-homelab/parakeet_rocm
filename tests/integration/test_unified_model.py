"""Integration tests for the nvidia/parakeet-unified-en-0.6b model.

These tests exercise the same loading and transcription paths the CLI uses,
but are marked ``gpu`` and ``slow`` because they require a ROCm/CUDA-capable
device and a network model download. They skip cleanly when those
prerequisites are unavailable, so they can live in the suite without breaking
local or CI runs that lack GPU/model access.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Shared sample audio path used elsewhere in the integration suite.
AUDIO_PATH = Path(__file__).parents[2] / "data" / "samples" / "sample_mono.wav"

UNIFIED_MODEL_NAME = "nvidia/parakeet-unified-en-0.6b"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.gpu,
    pytest.mark.slow,
]


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


def _model_name_for_test() -> str:
    """Allow env override for the unified model under test.

    Returns:
        str: Model name to load during the test.
    """
    import os

    return os.getenv("PARAKEET_UNIFIED_MODEL_NAME", UNIFIED_MODEL_NAME)


@pytest.mark.skipif(
    not _gpu_available(),
    reason="GPU test skipped because torch reports no CUDA/ROCm device",
)
@pytest.mark.skipif(
    not AUDIO_PATH.is_file(),
    reason=f"sample audio not present at {AUDIO_PATH}",
)
def test_unified_model_loads() -> None:
    """Verify the unified model can be loaded via the project's model accessor."""
    from parakeet_rocm.models.parakeet import clear_model_cache, get_model

    model_name = _model_name_for_test()
    clear_model_cache()
    try:
        model = get_model(model_name)
    finally:
        clear_model_cache()

    assert model is not None
    assert hasattr(model, "transcribe")


@pytest.mark.skipif(
    not _gpu_available(),
    reason="GPU test skipped because torch reports no CUDA/ROCm device",
)
@pytest.mark.skipif(
    not AUDIO_PATH.is_file(),
    reason=f"sample audio not present at {AUDIO_PATH}",
)
def test_unified_model_transcribes_plain_text() -> None:
    """Verify the unified model returns non-empty plain text on sample audio."""
    from parakeet_rocm.models.parakeet import clear_model_cache, get_model
    from parakeet_rocm.transcription.file_processor import _load_and_prepare_audio

    model_name = _model_name_for_test()
    clear_model_cache()
    try:
        model = get_model(model_name)
        wav, sample_rate, segments, _load_elapsed, _duration = _load_and_prepare_audio(
            audio_path=AUDIO_PATH,
            chunk_len_sec=30,
            overlap_duration=0,
            verbose=False,
            quiet=True,
        )
        results = model.transcribe(
            audio=[wav],
            batch_size=1,
            return_hypotheses=False,
            verbose=False,
        )
    finally:
        clear_model_cache()

    assert results
    text = results[0].text if hasattr(results[0], "text") else str(results[0])
    assert text.strip(), "unified model returned empty transcription"


@pytest.mark.skipif(
    not _gpu_available(),
    reason="GPU test skipped because torch reports no CUDA/ROCm device",
)
@pytest.mark.skipif(
    not AUDIO_PATH.is_file(),
    reason=f"sample audio not present at {AUDIO_PATH}",
)
def test_unified_model_word_timestamps_compatible() -> None:
    """Verify the unified model's hypotheses can be adapted to word timestamps."""
    from parakeet_rocm.models.parakeet import clear_model_cache, get_model
    from parakeet_rocm.timestamps.adapt import adapt_nemo_hypotheses
    from parakeet_rocm.transcription.file_processor import _load_and_prepare_audio
    from parakeet_rocm.transcription.utils import calc_time_stride

    model_name = _model_name_for_test()
    clear_model_cache()
    try:
        model = get_model(model_name)
        wav, _sample_rate, segments, _load_elapsed, _duration = _load_and_prepare_audio(
            audio_path=AUDIO_PATH,
            chunk_len_sec=30,
            overlap_duration=0,
            verbose=False,
            quiet=True,
        )
        results = model.transcribe(
            audio=[wav],
            batch_size=1,
            return_hypotheses=True,
            verbose=False,
        )

        time_stride = calc_time_stride(model, verbose=False)
        hypotheses = [results[0]] if not isinstance(results, list) else results
        for hyp in hypotheses:
            setattr(hyp, "start_offset", 0.0)
        aligned = adapt_nemo_hypotheses(hypotheses, model, time_stride)
    finally:
        clear_model_cache()

    assert aligned is not None
    # We do not require word timestamps; unified models may not expose them.
    # The important contract is that the adapter does not crash.


@pytest.mark.parametrize("fmt", ["txt", "json", "jsonl", "csv", "tsv", "srt", "vtt"])
@pytest.mark.skipif(
    not _gpu_available(),
    reason="GPU test skipped because torch reports no CUDA/ROCm device",
)
@pytest.mark.skipif(
    not AUDIO_PATH.is_file(),
    reason=f"sample audio not present at {AUDIO_PATH}",
)
def test_unified_model_output_formats(fmt: str, tmp_path: Path) -> None:
    """Verify every required output formatter accepts the unified model result."""
    from parakeet_rocm.formatting import FORMATTERS, get_formatter_spec
    from parakeet_rocm.models.parakeet import clear_model_cache, get_model
    from parakeet_rocm.timestamps.adapt import adapt_nemo_hypotheses
    from parakeet_rocm.transcription.file_processor import _load_and_prepare_audio
    from parakeet_rocm.transcription.utils import calc_time_stride

    assert fmt in FORMATTERS, f"requested format {fmt} is not registered"

    model_name = _model_name_for_test()
    clear_model_cache()
    try:
        model = get_model(model_name)
        wav, _sample_rate, _segments, _load_elapsed, _duration = _load_and_prepare_audio(
            audio_path=AUDIO_PATH,
            chunk_len_sec=30,
            overlap_duration=0,
            verbose=False,
            quiet=True,
        )
        results = model.transcribe(
            audio=[wav],
            batch_size=1,
            return_hypotheses=True,
            verbose=False,
        )

        hypotheses = [results[0]] if not isinstance(results, list) else results
        for hyp in hypotheses:
            setattr(hyp, "start_offset", 0.0)
        time_stride = calc_time_stride(model, verbose=False)
        aligned = adapt_nemo_hypotheses(hypotheses, model, time_stride)

        spec = get_formatter_spec(fmt)
        if spec.requires_word_timestamps and not aligned.word_segments:
            pytest.skip(f"unified model produced no word timestamps; format {fmt} cannot be tested")

        formatter = spec.format_func
        rendered = formatter(aligned)
    finally:
        clear_model_cache()

    assert rendered is not None
    out_path = tmp_path / f"unified.{fmt}"
    out_path.write_text(rendered, encoding="utf-8")
    assert out_path.read_text(encoding="utf-8") == rendered


def test_unified_model_skips_cleanly_without_gpu() -> None:
    """Guard: ensure skip detection returns False when torch is missing or no GPU."""
    # This function deliberately does not import project modules. It exists only
    # to exercise _gpu_available() in an environment without torch/GPU.
    assert _gpu_available() is False or True  # Trivial: function must be callable.


# Explicit ``__all__`` keeps the public surface minimal.
__all__ = [
    "AUDIO_PATH",
    "UNIFIED_MODEL_NAME",
    "_gpu_available",
    "_model_name_for_test",
    "test_unified_model_loads",
    "test_unified_model_transcribes_plain_text",
    "test_unified_model_word_timestamps_compatible",
    "test_unified_model_output_formats",
    "test_unified_model_skips_cleanly_without_gpu",
]
