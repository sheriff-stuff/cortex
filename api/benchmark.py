"""Pipeline benchmark: run the full pipeline with detailed timing instrumentation."""

import gc
import json
import os
import platform
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from api.config import Config


@dataclass
class TimingRecord:
    name: str
    start: float = 0.0
    end: float = 0.0
    children: list["TimingRecord"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def elapsed(self) -> float:
        return self.end - self.start


class StageTimer:
    """Hierarchical timer that tracks nested stages."""

    def __init__(self):
        self.root = TimingRecord(name="pipeline")
        self._stack: list[TimingRecord] = [self.root]

    @contextmanager
    def stage(self, name: str, **metadata):
        record = TimingRecord(name=name, start=time.perf_counter(), metadata=metadata)
        self._stack[-1].children.append(record)
        self._stack.append(record)
        try:
            yield record
        finally:
            record.end = time.perf_counter()
            self._stack.pop()

    def _record_to_dict(self, record: TimingRecord) -> dict:
        d = {
            "name": record.name,
            "elapsed_seconds": round(record.elapsed, 3),
        }
        if record.metadata:
            d["metadata"] = record.metadata
        if record.children:
            d["children"] = [self._record_to_dict(c) for c in record.children]
        return d

    def to_dict(self) -> dict:
        return self._record_to_dict(self.root)


def _get_system_info() -> dict:
    """Collect system information for the report."""
    info = {
        "os": f"{platform.system()} {platform.version()}",
        "python": platform.python_version(),
        "cpu": platform.processor() or "unknown",
    }

    # RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
        info["ram_available_gb"] = round(mem.available / (1024 ** 3), 1)
    except ImportError:
        pass

    # Torch + CUDA
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["cuda_version"] = torch.version.cuda or "unknown"
            info["gpu_name"] = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory
            info["gpu_memory_gb"] = round(gpu_mem / (1024 ** 3), 1)
    except ImportError:
        info["torch"] = "not installed"
    except Exception:
        info.setdefault("torch", "installed (error collecting CUDA/GPU info)")

    # WhisperX
    try:
        import whisperx
        info["whisperx"] = getattr(whisperx, "__version__", "installed (version unknown)")
    except ImportError:
        info["whisperx"] = "not installed"

    return info


def _get_process_memory_mb() -> float:
    """Get current process RSS in MB."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2)
    except ImportError:
        return 0.0


def _get_gpu_memory_mb() -> float:
    """Get current GPU memory usage in MB."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 ** 2)
    except ImportError:
        pass
    return 0.0


def _get_gpu_memory_peak_mb() -> float:
    """Get peak GPU memory usage in MB."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024 ** 2)
    except ImportError:
        pass
    return 0.0


def benchmark_pipeline(file_path: Path, config: Config, no_llm: bool = False,
                       save_to_db: bool = False) -> dict:
    """Run the full pipeline with detailed timing. Returns a benchmark report dict."""
    from api.audio import extract_audio, get_duration, validate_input
    from api.diarize import diarize, map_speaker_label, resolve_hf_token
    from api.extractor import ExtractionResult, merge_extractions, parse_llm_response
    from api.llm import check_model_available, check_ollama, chunk_transcript, query_ollama
    from api.markdown import build_sidecar_dict, render, write_output
    from api.prompts import build_extraction_prompt, format_transcript_for_llm
    from api.quality import analyze_quality
    from api.transcribe import Segment, TranscriptResult

    timer = StageTimer()
    mem_start = _get_process_memory_mb()

    # Reset GPU peak tracking
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except ImportError:
        pass

    timer.root.start = time.perf_counter()

    # --- System & input info ---
    system_info = _get_system_info()
    file_size_mb = file_path.stat().st_size / (1024 ** 2)

    # --- Stage 1: Validate input ---
    with timer.stage("validate_input"):
        file_type = validate_input(file_path)

    # --- Stage 2: Get duration ---
    with timer.stage("get_duration"):
        duration = get_duration(file_path)

    # --- Stage 3: Extract audio ---
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        with timer.stage("extract_audio", file_type=file_type):
            audio_path = extract_audio(file_path, tmp_path)

        wav_size_mb = audio_path.stat().st_size / (1024 ** 2)

        # --- Stage 4: Transcription (broken into sub-stages) ---
        with timer.stage("transcription"):
            import torch
            import whisperx

            device = config.whisper_device
            compute_type = config.whisper_compute_type

            if device == "cuda" and not torch.cuda.is_available():
                device = "cpu"
                compute_type = "int8"

            # 4a: Load Whisper model
            with timer.stage("load_whisper_model", model=config.whisper_model,
                             device=device, compute_type=compute_type):
                model = whisperx.load_model(
                    config.whisper_model, device=device, compute_type=compute_type,
                )

            # 4b: Load audio
            with timer.stage("load_audio"):
                audio = whisperx.load_audio(str(audio_path))

            # 4c: Transcribe
            with timer.stage("transcribe", batch_size=16):
                result = model.transcribe(audio, batch_size=16)
                language = result.get("language", "en")
                raw_segment_count = len(result.get("segments", []))

            # 4d: Load alignment model
            with timer.stage("load_align_model", language=language):
                align_model, align_metadata = whisperx.load_align_model(
                    language_code=language, device=device,
                )

            # 4e: Align
            with timer.stage("align", segment_count=raw_segment_count):
                result = whisperx.align(
                    result["segments"], align_model, align_metadata,
                    audio, device, return_char_alignments=False,
                )

            # 4f: Diarization
            hf_token = resolve_hf_token(config.hf_token)
            with timer.stage("diarization"):
                from whisperx.diarize import DiarizationPipeline

                with timer.stage("load_diarization_model"):
                    try:
                        diarize_model = DiarizationPipeline(
                            token=hf_token, device=device,
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

                with timer.stage("run_diarization"):
                    diarize_segments = diarize_model(audio)

                with timer.stage("assign_speakers"):
                    result = whisperx.assign_word_speakers(diarize_segments, result)

            # Build structured segments
            speaker_map: dict[str, str] = {}
            segments: list[Segment] = []
            word_segments: list[dict] = []

            for seg in result.get("segments", []):
                raw_speaker = seg.get("speaker", "UNKNOWN")
                speaker = map_speaker_label(raw_speaker, speaker_map)
                words = seg.get("words", [])
                avg_conf = (sum(w.get("score", 0.0) for w in words) / len(words)) if words else 0.0
                segments.append(Segment(
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    speaker=speaker,
                    text=seg.get("text", "").strip(),
                    confidence=avg_conf,
                ))
                word_segments.extend(words)

            # Free GPU memory
            del model
            gc.collect()
            if device == "cuda":
                torch.cuda.empty_cache()

            transcript = TranscriptResult(
                segments=segments,
                speaker_count=len(speaker_map),
                language=language,
                word_segments=word_segments,
            )

        mem_after_transcription = _get_process_memory_mb()
        gpu_peak_after_transcription = _get_gpu_memory_peak_mb()

        if not transcript.segments:
            raise RuntimeError("No speech detected in the audio file.")

        # --- Stage 5: Quality analysis ---
        with timer.stage("quality_analysis", segment_count=len(transcript.segments)):
            quality_flags = analyze_quality(transcript)

        # --- Stage 6: LLM extraction ---
        extraction = None
        llm_stats = {}
        if not no_llm:
            with timer.stage("llm_extraction"):
                with timer.stage("check_ollama"):
                    ollama_ok = check_ollama(config)
                if not ollama_ok:
                    raise RuntimeError(
                        "Ollama is not running. Start with 'ollama serve' or use --no-llm."
                    )

                with timer.stage("check_model"):
                    model_ok = check_model_available(config)
                if not model_ok:
                    raise RuntimeError(
                        f"Model '{config.llm_model}' not found. "
                        f"Pull with 'ollama pull {config.llm_model}'."
                    )

                with timer.stage("chunk_transcript") as chunk_rec:
                    chunks = chunk_transcript(segments, config)
                    chunk_rec.metadata["chunk_count"] = len(chunks)
                    chunk_rec.metadata["segments_per_chunk"] = [len(c) for c in chunks]

                chunk_results: list[dict] = []
                prompt_sizes: list[int] = []
                estimated_tokens: list[int] = []

                for i, chunk in enumerate(chunks):
                    with timer.stage(f"chunk_{i + 1}", chunk_index=i + 1,
                                     segment_count=len(chunk)):
                        with timer.stage("build_prompt"):
                            transcript_text = format_transcript_for_llm(chunk)
                            prompt = build_extraction_prompt(transcript_text)
                            prompt_size = len(prompt)
                            prompt_sizes.append(prompt_size)
                            estimated_tokens.append(int(len(transcript_text.split()) * 1.3))

                        with timer.stage("query_ollama",
                                         prompt_chars=prompt_size) as ollama_rec:
                            response = query_ollama(prompt, config)
                            ollama_rec.metadata["response_chars"] = len(response)

                        with timer.stage("parse_response"):
                            parsed = parse_llm_response(response)
                            chunk_results.append(parsed)

                with timer.stage("merge_results", chunk_count=len(chunk_results)):
                    extraction = merge_extractions(chunk_results)

                llm_stats = {
                    "chunk_count": len(chunks),
                    "prompt_sizes_chars": prompt_sizes,
                    "estimated_tokens_per_chunk": estimated_tokens,
                }

        # --- Stage 7: Render markdown ---
        with timer.stage("render_markdown"):
            content = render(
                source_file=file_path, duration=duration, transcript=transcript,
                extraction=extraction, quality_flags=quality_flags, config=config,
            )

        # --- Stage 8: Write output ---
        output_dir = Path(config.default_output_dir)
        with timer.stage("write_output"):
            sidecar = build_sidecar_dict(
                source_file=file_path, duration=duration, transcript=transcript,
                extraction=extraction, quality_flags=quality_flags, config=config,
            )
            output_path = write_output(content, output_dir)

        # --- Stage 9: Save to database (opt-in) ---
        if save_to_db:
            with timer.stage("save_to_database"):
                from api.db import MeetingRepository, create_db_engine, init_db
                engine = create_db_engine(config.database_url)
                init_db(engine)
                repo = MeetingRepository(engine)
                sidecar.setdefault("filename", output_path.name)
                if not repo.meeting_exists(sidecar["filename"]):
                    repo.save_meeting(sidecar, content)

    timer.root.end = time.perf_counter()
    mem_end = _get_process_memory_mb()

    # --- Build report ---
    total_words = sum(len(seg.text.split()) for seg in transcript.segments)

    transcript_stats = {
        "segment_count": len(transcript.segments),
        "speaker_count": transcript.speaker_count,
        "word_count": total_words,
        "language": transcript.language,
    }

    extraction_stats = {}
    if extraction:
        extraction_stats = {
            "topic_count": len(extraction.topics),
            "decision_count": len(extraction.decisions),
            "action_item_count": len(extraction.action_items),
            "question_count": len(extraction.questions),
            "keyword_count": len(extraction.keywords),
        }

    quality_summary = {}
    if quality_flags:
        from collections import Counter
        type_counts = Counter(f.type for f in quality_flags)
        quality_summary = {
            "total_flags": len(quality_flags),
            "by_type": dict(type_counts),
        }

    report = {
        "system": system_info,
        "input": {
            "file": file_path.name,
            "file_path": str(file_path.resolve()),
            "format": file_type,
            "duration_seconds": round(duration, 2),
            "duration_formatted": f"{int(duration // 60)}m {int(duration % 60)}s",
            "file_size_mb": round(file_size_mb, 1),
            "wav_size_mb": round(wav_size_mb, 1),
        },
        "config": {
            "whisper_model": config.whisper_model,
            "whisper_device": config.whisper_device,
            "whisper_compute_type": config.whisper_compute_type,
            "llm_model": config.llm_model if not no_llm else "skipped",
            "chunk_max_tokens": config.chunk_max_tokens,
            "chunk_overlap_seconds": config.chunk_overlap_seconds,
        },
        "timing": timer.to_dict(),
        "transcript": transcript_stats,
        "extraction": extraction_stats,
        "llm": llm_stats,
        "quality": quality_summary,
        "memory": {
            "process_rss_start_mb": round(mem_start, 1),
            "process_rss_after_transcription_mb": round(mem_after_transcription, 1),
            "process_rss_end_mb": round(mem_end, 1),
            "gpu_peak_after_transcription_mb": round(gpu_peak_after_transcription, 1),
        },
        "output": {
            "markdown_path": str(output_path),
            "markdown_size_bytes": output_path.stat().st_size,
        },
    }

    return report


def _format_timing_line(name: str, elapsed: float, total: float, depth: int,
                        max_bar_width: int = 40) -> str:
    """Format a single timing line for the text report."""
    indent = "  " * depth
    padded_name = f"{indent}{name}"
    pct = (elapsed / total * 100) if total > 0 else 0.0
    bar_len = int(pct / 100 * max_bar_width)
    bar = "\u2588" * bar_len

    if elapsed >= 60:
        time_str = f"{elapsed / 60:.1f}m"
    else:
        time_str = f"{elapsed:.2f}s"

    return f"{padded_name:<38} {time_str:>8}  {pct:>5.1f}%  {bar}"


def _walk_timing(record: dict, total: float, depth: int, lines: list[str]) -> None:
    """Recursively walk the timing tree and format lines."""
    lines.append(_format_timing_line(
        record["name"], record["elapsed_seconds"], total, depth,
    ))
    for child in record.get("children", []):
        _walk_timing(child, total, depth + 1, lines)


def format_report_text(report: dict) -> str:
    """Format the benchmark report as human-readable text."""
    lines: list[str] = []
    sep = "\u2550" * 62
    thin_sep = "\u2500" * 62

    lines.append("")
    lines.append(sep)
    lines.append("  PIPELINE BENCHMARK REPORT")
    lines.append(sep)
    lines.append("")

    # System
    sys_info = report["system"]
    lines.append("System")
    lines.append(f"  OS:             {sys_info['os']}")
    lines.append(f"  Python:         {sys_info['python']}")
    lines.append(f"  CPU:            {sys_info['cpu']}")
    if "ram_total_gb" in sys_info:
        lines.append(f"  RAM:            {sys_info['ram_total_gb']} GB total, "
                     f"{sys_info['ram_available_gb']} GB available")
    if "torch" in sys_info:
        torch_line = f"  Torch:          {sys_info['torch']}"
        if sys_info.get("cuda_available"):
            torch_line += f" (CUDA {sys_info.get('cuda_version', '?')})"
        lines.append(torch_line)
    if sys_info.get("gpu_name"):
        lines.append(f"  GPU:            {sys_info['gpu_name']} "
                     f"({sys_info.get('gpu_memory_gb', '?')} GB)")
    if "whisperx" in sys_info:
        lines.append(f"  WhisperX:       {sys_info['whisperx']}")
    lines.append("")

    # Input
    inp = report["input"]
    lines.append("Input")
    lines.append(f"  File:           {inp['file']}")
    lines.append(f"  Format:         {inp['format']}")
    lines.append(f"  Duration:       {inp['duration_formatted']}")
    lines.append(f"  File size:      {inp['file_size_mb']} MB")
    lines.append(f"  WAV size:       {inp['wav_size_mb']} MB")
    lines.append("")

    # Config
    cfg = report["config"]
    lines.append("Config")
    lines.append(f"  Whisper model:  {cfg['whisper_model']}")
    lines.append(f"  Device:         {cfg['whisper_device']} / {cfg['whisper_compute_type']}")
    lines.append(f"  LLM model:      {cfg['llm_model']}")
    lines.append(f"  Chunk tokens:   {cfg['chunk_max_tokens']}")
    lines.append(f"  Chunk overlap:  {cfg['chunk_overlap_seconds']}s")
    lines.append("")

    # Timing
    lines.append(thin_sep)
    lines.append("  STAGE TIMING")
    lines.append(thin_sep)
    lines.append("")
    lines.append(f"{'Stage':<38} {'Time':>8}  {'%':>5}   Bar")
    lines.append("\u2500" * 70)

    timing = report["timing"]
    total = timing["elapsed_seconds"]
    for child in timing.get("children", []):
        _walk_timing(child, total, 0, lines)

    lines.append("\u2500" * 70)
    if total >= 60:
        total_str = f"{total / 60:.1f}m"
    else:
        total_str = f"{total:.2f}s"
    lines.append(f"{'TOTAL':<38} {total_str:>8}  100.0%")
    lines.append("")

    # Transcript stats
    ts = report["transcript"]
    lines.append("Transcript")
    lines.append(f"  Segments:       {ts['segment_count']}")
    lines.append(f"  Speakers:       {ts['speaker_count']}")
    lines.append(f"  Words:          {ts['word_count']:,}")
    lines.append(f"  Language:       {ts['language']}")
    lines.append("")

    # LLM stats
    if report.get("llm"):
        llm = report["llm"]
        lines.append("LLM Extraction")
        lines.append(f"  Chunks:         {llm['chunk_count']}")
        if llm.get("estimated_tokens_per_chunk"):
            avg_tokens = sum(llm["estimated_tokens_per_chunk"]) // len(llm["estimated_tokens_per_chunk"])
            lines.append(f"  Avg tokens:     ~{avg_tokens:,} per chunk")
        lines.append("")

    # Extraction stats
    if report.get("extraction"):
        ext = report["extraction"]
        lines.append("Extraction Results")
        lines.append(f"  Topics:         {ext['topic_count']}")
        lines.append(f"  Decisions:      {ext['decision_count']}")
        lines.append(f"  Action items:   {ext['action_item_count']}")
        lines.append(f"  Questions:      {ext['question_count']}")
        lines.append(f"  Keywords:       {ext['keyword_count']}")
        lines.append("")

    # Quality
    if report.get("quality"):
        q = report["quality"]
        type_str = ", ".join(f"{count} {typ}" for typ, count in q["by_type"].items())
        lines.append(f"Quality Flags:    {q['total_flags']} ({type_str})")
        lines.append("")

    # Memory
    mem = report["memory"]
    lines.append("Memory")
    lines.append(f"  Process RSS start:                {mem['process_rss_start_mb']:.0f} MB")
    lines.append(f"  Process RSS after transcription:   {mem['process_rss_after_transcription_mb']:.0f} MB")
    lines.append(f"  Process RSS end:                   {mem['process_rss_end_mb']:.0f} MB")
    if mem["gpu_peak_after_transcription_mb"] > 0:
        lines.append(f"  GPU peak (transcription):          {mem['gpu_peak_after_transcription_mb']:.0f} MB")
    lines.append("")

    # Processing speed
    inp_duration = report["input"]["duration_seconds"]
    if total > 0:
        realtime_ratio = inp_duration / total
        lines.append(f"Speed:            {realtime_ratio:.2f}x realtime "
                     f"({inp['duration_formatted']} audio in {total_str})")
    lines.append("")

    return "\n".join(lines)
