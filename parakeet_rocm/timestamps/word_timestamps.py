"""Utilities for extracting word-level timestamps from NeMo ASR hypotheses."""

from nemo.collections.asr.models import ASRModel
from nemo.collections.asr.parts.utils.rnnt_utils import Hypothesis

from parakeet_rocm.timestamps.models import Word


def get_word_timestamps(
    hypotheses: list[Hypothesis],
    model: ASRModel,
    time_stride: float | None = None,
) -> list[Word]:
    """
    Extract word-level timestamps from a list of Transducer hypotheses.
    
    Converts per-token timestamps and token IDs in each Hypothesis into Word objects with start and end times inferred from token timestamps and SentencePiece word boundaries (leading "▁"). Overlapping words from chunked/overlapping hypotheses are de-duplicated with a small tolerance.
    
    Parameters:
        hypotheses: List of NeMo `Hypothesis` objects containing `y_sequence` and `timestamp` arrays.
        model: ASR model instance whose tokenizer is used to map token IDs to text.
        time_stride: Optional multiplier to convert token-frame indices into seconds (frame duration); if None timestamps are used as-is.
    
    Returns:
        list[Word]: List of words with `word` (text), `start` (seconds), `end` (seconds), and `score` set to `None`.
    """
    all_words: list[Word] = []
    # SentencePiece-based tokenizers (used by NeMo ASR models) encode the beginning
    # of a new word with a leading "▁" character.  QuartzNet-style char tokenizers
    # sometimes expose `tokenizer.space`, but this attribute is not present on
    # `SentencePieceTokenizer`.  Hence we detect word boundaries based on this
    # leading marker instead of relying on a dedicated space token.

    for hypo in hypotheses:
        if not hasattr(hypo, "y_sequence") or not hasattr(hypo, "timestamp"):
            continue

        # Get the token IDs from the hypothesis
        token_ids = hypo.y_sequence.detach().cpu().numpy()
        # Get the timestamps for each token
        timestamps_raw = hypo.timestamp.detach().cpu().numpy().astype(float)
        if time_stride is not None:
            timestamps = timestamps_raw * time_stride
        else:
            timestamps = timestamps_raw

        words_for_hypo = []
        current_word = []
        word_start_time = -1

        for i, token_id_np in enumerate(token_ids):
            token_id = int(token_id_np)  # ensure native int for SentencePiece SWIG
            token_text = model.tokenizer.ids_to_tokens([token_id])[0]
            time = timestamps[i] + getattr(hypo, "start_offset", 0.0)

            # Detect start of a new word. SentencePiece denotes it via leading '▁'.
            is_word_start = token_text.startswith("▁")

            if is_word_start and current_word:
                # Finish previous word
                word_text = model.tokenizer.ids_to_text(current_word)
                words_for_hypo.append(
                    Word(
                        word=word_text.lstrip("▁"),
                        start=word_start_time,
                        end=time,
                        score=None,
                    )
                )
                current_word = []
                word_start_time = time  # new word starts now

            if not current_word:
                word_start_time = time

            current_word.append(token_id)

        # Add the last word if any
        if current_word:
            word_text = model.tokenizer.ids_to_text(current_word)
            end_time = timestamps[-1] + getattr(hypo, "start_offset", 0.0)
            words_for_hypo.append(
                Word(
                    word=word_text.lstrip("▁"),
                    start=word_start_time,
                    end=end_time,
                    score=None,
                )
            )

        all_words.extend(words_for_hypo)

    # Post-process to remove duplicates arising from overlapping chunks.
    if not all_words:
        return []

    all_words.sort(key=lambda w: w.start)
    deduped: list[Word] = []
    last_end = -1.0
    min_gap = 0.03  # 30 ms tolerance for overlap

    for w in all_words:
        if w.start < last_end - min_gap:
            # This word is (almost) entirely contained in the previous window; skip it.
            continue
        deduped.append(w)
        last_end = w.end

    return deduped