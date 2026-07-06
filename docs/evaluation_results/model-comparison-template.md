# Model comparison result template

Copy this template, rename it with the date and hardware, and fill in the
measurements from a real run of `scripts/evaluate_model.py`.

## Metadata

- Date: YYYY-MM-DD
- Hardware: e.g. AMD Radeon RX 7900 XTX / ROCm 7.0
- Baseline model: nvidia/parakeet-tdt-0.6b-v3
- Candidate model: nvidia/parakeet-unified-en-0.6b
- Audio source: e.g. data/samples/sample_mono.wav
- Evaluation script: `pdm run python -m scripts.evaluate_model run ...`
- Command flags used: (chunk length, batch size, word timestamps on/off, etc.)

## Observations

### Baseline (nvidia/parakeet-tdt-0.6b-v3)

- Runtime: ___ seconds
- Load time: ___ seconds
- Word count: ___
- Segment count: ___
- Timestamp compatible: yes/no
- Transcription excerpt: "..."

### Candidate (nvidia/parakeet-unified-en-0.6b)

- Runtime: ___ seconds
- Load time: ___ seconds
- Word count: ___
- Segment count: ___
- Timestamp compatible: yes/no
- Transcription excerpt: "..."

### Comparison

- Text similarity ratio: ___
- Notable transcription differences: ___
- Timestamp compatibility notes: ___
- Output format compatibility: txt/json/jsonl/csv/tsv/srt/vtt all rendered?

## Conclusion

Should the candidate model become the new default? What further evidence is
needed?

## Attachments

- JSON report path/name
- Markdown report path/name
