"""WhisperX transcription with speaker diarization."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from api.config import Config
from api.diarize import diarize, map_speaker_label, resolve_hf_token


@dataclass
class Segment:
    start: float
    end: float
    speaker: str
    text: str
    confidence: float = 1.0


@dataclass
class TranscriptResult:
    segments: list[Segment] = field(default_factory=list)
    speaker_count: int = 0
    language: str = ""
    word_segments: list[dict] = field(default_factory=list)


def transcribe(
    audio_path: Path,
    config: Config,
    progress_callback: Callable[[str], None] | None = None,
) -> TranscriptResult:
    """Run full WhisperX pipeline: transcribe -> align -> diarize."""
    import whisperx
    import torch

    device = config.whisper_device
    compute_type = config.whisper_compute_type

    # Fallback to CPU if CUDA not available
    if device == "cuda" and not torch.cuda.is_available():
        device = "cpu"
        compute_type = "int8"

    if progress_callback:
        progress_callback("Loading Whisper model...")

    model = whisperx.load_model(
        config.whisper_model,
        device=device,
        compute_type=compute_type,
    )

    if progress_callback:
        progress_callback("Transcribing audio...")

    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=16)
    language = result.get("language", "en")

    if progress_callback:
        progress_callback("Aligning transcript...")

    align_model, align_metadata = whisperx.load_align_model(
        language_code=language,
        device=device,
    )
    result = whisperx.align(
        result["segments"],
        align_model,
        align_metadata,
        audio,
        device,
        return_char_alignments=False,
    )

    hf_token = resolve_hf_token(config.hf_token)
    result = diarize(audio, result, device, hf_token, progress_callback)

    # Build structured segments
    speaker_map: dict[str, str] = {}
    segments: list[Segment] = []
    word_segments: list[dict] = []

    for seg in result.get("segments", []):
        raw_speaker = seg.get("speaker", "UNKNOWN")
        speaker = map_speaker_label(raw_speaker, speaker_map)

        # Calculate average word confidence
        words = seg.get("words", [])
        if words:
            avg_conf = sum(w.get("score", 0.0) for w in words) / len(words)
        else:
            avg_conf = 0.0

        segments.append(Segment(
            start=seg.get("start", 0.0),
            end=seg.get("end", 0.0),
            speaker=speaker,
            text=seg.get("text", "").strip(),
            confidence=avg_conf,
        ))
        word_segments.extend(words)

    # Free GPU memory
    import gc
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    return TranscriptResult(
        segments=segments,
        speaker_count=len(speaker_map),
        language=language,
        word_segments=word_segments,
    )
