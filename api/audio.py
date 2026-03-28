"""Audio handling: format validation, video-to-audio extraction, duration detection."""

import shutil
import subprocess
from pathlib import Path

SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".aac"}
SUPPORTED_VIDEO = {".mp4", ".mkv", ".avi", ".mov"}
SUPPORTED_ALL = SUPPORTED_AUDIO | SUPPORTED_VIDEO


def get_ffmpeg_path() -> str:
    """Find ffmpeg binary: prefer system install, fallback to imageio-ffmpeg."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    raise FileNotFoundError(
        "ffmpeg not found. Install it via:\n"
        "  Windows: winget install ffmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Linux:   sudo apt install ffmpeg\n"
        "Or install imageio-ffmpeg: pip install imageio-ffmpeg"
    )


def validate_input(file_path: Path) -> str:
    """Validate file format. Returns 'audio' or 'video'."""
    ext = file_path.suffix.lower()
    if ext in SUPPORTED_AUDIO:
        return "audio"
    if ext in SUPPORTED_VIDEO:
        return "video"
    raise ValueError(
        f"Unsupported format '{ext}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_ALL))}"
    )


def extract_audio(file_path: Path, work_dir: Path) -> Path:
    """Extract audio from video file as WAV, or convert audio to WAV if needed.

    Returns path to a WAV file ready for transcription.
    """
    validate_input(file_path)
    ffmpeg = get_ffmpeg_path()

    # If already WAV, use directly
    if file_path.suffix.lower() == ".wav":
        return file_path

    # Convert to WAV (16kHz mono for Whisper)
    output_path = work_dir / f"{file_path.stem}.wav"
    cmd = [
        ffmpeg,
        "-i", str(file_path),
        "-vn",                # strip video
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",       # 16kHz sample rate
        "-ac", "1",           # mono
        "-y",                 # overwrite
        str(output_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed to extract audio:\n{result.stderr[:500]}"
        )
    return output_path


def get_ffprobe_path() -> str:
    """Find ffprobe binary: prefer system install, fallback to imageio-ffmpeg."""
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe
    try:
        import imageio_ffmpeg
        candidate = Path(imageio_ffmpeg.get_ffmpeg_exe()).parent / "ffprobe"
        if candidate.exists():
            return str(candidate)
    except ImportError:
        pass
    raise FileNotFoundError(
        "ffprobe not found. Install ffmpeg via:\n"
        "  Windows: winget install ffmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Linux:   sudo apt install ffmpeg"
    )


def get_duration(file_path: Path) -> float:
    """Get audio/video duration in seconds using ffprobe."""
    ffprobe = get_ffprobe_path()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:500]}")
    return float(result.stdout.strip())
