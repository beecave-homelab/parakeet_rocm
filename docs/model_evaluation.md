# Model evaluation

This document describes how to compare the default Parakeet ASR model with
`nvidia/parakeet-unified-en-0.6b` (or any other NeMo ASR model) using the
evaluation tooling added for Issue #41.

## Quick start

Evaluate the unified model against the default model on a single audio file:

```bash
pdm run python -m scripts.evaluate_model run data/samples/sample_mono.wav
```

The script writes machine-readable JSON and human-readable Markdown reports to
`data/evaluation_results/` by default.

## What is compared

The evaluation script exercises the same transcription pipeline the CLI uses:

- model loading via `parakeet_rocm.models.parakeet.get_model`
- audio loading and chunked segmentation
- inference with `return_hypotheses=True`
- word-timestamp adaptation via `parakeet_rocm.timestamps.adapt`
- all built-in output formatters: `txt`, `json`, `jsonl`, `csv`, `tsv`, `srt`, `vtt`
- benchmark metrics via `parakeet_rocm.benchmarks.BenchmarkCollector`
- ROCm GPU telemetry (load and VRAM) via `parakeet_rocm.benchmarks.GpuUtilSampler`
  when `pyamdgpuinfo` is installed; otherwise GPU stats are omitted and the
  report records `none`

For each audio file the script reports:

- transcription text from both models
- runtime and model-load time
- audio duration in seconds
- GPU load/VRAM telemetry when available
- word and segment counts
- timestamp compatibility flag and notes
- text similarity ratio between the two transcriptions
- paths to generated per-format output files

## Commands

### Single file

```bash
pdm run python -m scripts.evaluate_model run data/samples/sample_mono.wav \
  --candidate nvidia/parakeet-unified-en-0.6b \
  --output-dir data/evaluation_results
```

### Directory of audio files

```bash
pdm run python -m scripts.evaluate_model run data/samples/ \
  --output-dir data/evaluation_results
```

### Disable word timestamps

Some models return plain text more reliably than timestamped hypotheses:

```bash
pdm run python -m scripts.evaluate_model run data/samples/sample_mono.wav \
  --no-word-timestamps
```

### Custom baseline or candidate

```bash
pdm run python -m scripts.evaluate_model run data/samples/sample_mono.wav \
  --baseline nvidia/parakeet-tdt-0.6b-v2 \
  --candidate nvidia/parakeet-unified-en-0.6b
```

## Recording results

When you have run an evaluation on a real ROCm/CUDA machine:

1. Copy the generated Markdown report from
   `data/evaluation_results/evaluation_<baseline>_vs_<candidate>.md`.
2. Rename it with the date and hardware, for example
   `2026-07-05_rtx4090_parakeet-tdt-0.6b-v3_vs_parakeet-unified-en-0.6b.md`.
3. Place it in `docs/evaluation_results/`.
4. Fill in the template fields at the top of the file.

This keeps evaluation evidence under version control so the project can decide,
based on reproducible data, whether to change the default model.

## Tests

GPU/integration tests for the unified model live in
`tests/integration/test_unified_model.py`. GPU-dependent tests are marked
`integration`, `gpu`, and `slow` and skip cleanly when no GPU, sample audio, or
`CI=true` environment is detected. The non-GPU availability test still runs in
ordinary CI.

Run only non-GPU tests locally:

```bash
pdm run pytest tests/integration/test_unified_model.py -m 'not gpu' -v
```

Run GPU tests on a machine with the model available:

```bash
pdm run pytest tests/integration/test_unified_model.py -m gpu -v
```

## Known limitations

- The unified model may not expose word-level timestamps in the same format as
  the Parakeet-TDT model. The evaluation script records compatibility rather
  than failing; see `timestamp_compatible` and `timestamp_notes` in the JSON
  report.
- Full evaluation requires a ROCm/CUDA GPU and a network connection to download
  the candidate model. Running without those resources produces skipped tests
  and empty reports but does not break the suite.
- GPU memory and utilization telemetry are captured whenever `pyamdgpuinfo` is
  installed. If the dependency is missing, the sampler logs a warning and the
  report records `gpu_stats: none`. Installing `pyamdgpuinfo` still does not
  require torch/NeMo; the telemetry path is separate and degrades gracefully.
