"""Speaker diarization via pyannote (through WhisperX)."""

from typing import Callable


def resolve_hf_token(config_token: str) -> str | None:
    """Return a HuggingFace token from config or cached login."""
    token = config_token or None
    if token is None:
        try:
            from huggingface_hub import HfFolder
            token = HfFolder.get_token()
        except ImportError:
            pass
    return token


def diarize(
    audio,
    aligned_result: dict,
    device: str,
    hf_token: str | None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict:
    """Run speaker diarization and assign speakers to transcript segments.

    Returns the aligned result dict with speaker labels added.
    """
    import whisperx
    from whisperx.diarize import DiarizationPipeline

    if progress_callback:
        progress_callback("Identifying speakers...")

    try:
        diarize_model = DiarizationPipeline(
            token=hf_token,
            device=device,
        )
    except Exception as e:
        if "403" in str(e) or "gated" in str(e).lower() or "restricted" in str(e).lower():
            raise RuntimeError(
                "Cannot access the pyannote diarization model. You need to:\n"
                "1. Visit https://huggingface.co/pyannote/speaker-diarization-community-1\n"
                "2. Accept the user conditions\n"
                "3. Make sure your HuggingFace token is set (run: huggingface-cli login)"
            ) from e
        raise

    diarize_segments = diarize_model(audio)
    return whisperx.assign_word_speakers(diarize_segments, aligned_result)


def map_speaker_label(raw_label: str, speaker_map: dict[str, str]) -> str:
    """Map pyannote labels like 'SPEAKER_00' to 'Speaker 1'."""
    if raw_label not in speaker_map:
        idx = len(speaker_map) + 1
        speaker_map[raw_label] = f"Speaker {idx}"
    return speaker_map[raw_label]
