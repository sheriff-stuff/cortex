"""Main pipeline orchestrator: file -> structured Markdown notes."""

import os
import sys
import tempfile
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from api.config import Config

console = Console()


def process_meeting(file_path: Path, config: Config, no_llm: bool = False) -> Path:
    """Process a meeting recording into structured Markdown notes.

    Returns the path to the generated Markdown file.
    """
    from api.audio import extract_audio, get_duration, validate_input
    from api.extractor import ExtractionResult, extract_from_transcript
    from api.llm import check_llm, check_llm_model_available
    from api.markdown import build_sidecar_dict, render, write_output
    from api.quality import analyze_quality
    from api.transcribe import transcribe

    output_dir = Path(config.default_output_dir)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:

        # Step 1: Validate input
        main_task = progress.add_task("Processing meeting...", total=None)
        progress.update(main_task, description="Validating input file...")
        file_type = validate_input(file_path)
        console.print(f"  Input: [cyan]{file_path.name}[/] ({file_type})")

        # Step 2: Get duration
        progress.update(main_task, description="Reading file info...")
        duration = get_duration(file_path)
        console.print(f"  Duration: [cyan]{int(duration // 60)}m {int(duration % 60)}s[/]")

        # Step 3: Extract audio
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            if file_type == "video":
                progress.update(main_task, description="Extracting audio from video...")
                audio_path = extract_audio(file_path, tmp_path)
                console.print("  Audio extracted from video")
            else:
                audio_path = extract_audio(file_path, tmp_path)

            # Step 4: Transcribe
            progress.update(main_task, description="Transcribing audio...")

            def transcribe_callback(msg: str) -> None:
                progress.update(main_task, description=msg)

            transcript = transcribe(audio_path, config, progress_callback=transcribe_callback)
            console.print(f"  Transcription complete: [cyan]{len(transcript.segments)}[/] segments, [cyan]{transcript.speaker_count}[/] speakers")

            if not transcript.segments:
                console.print("[yellow]Warning: No speech detected in the audio file.[/]")
                raise SystemExit(1)

            # Step 5: Quality analysis
            progress.update(main_task, description="Analyzing audio quality...")
            quality_flags = analyze_quality(transcript)
            if quality_flags:
                console.print(f"  Quality flags: [yellow]{len(quality_flags)}[/] issues found")

            # Step 6: LLM extraction
            extraction = None
            if not no_llm:
                progress.update(main_task, description="Checking LLM...")

                if not check_llm(config):
                    if config.llm_provider == "ollama":
                        console.print(
                            "[bold red]Error:[/] Ollama is not running. "
                            "Start it with [cyan]ollama serve[/] or use [cyan]--no-llm[/] for transcript only."
                        )
                    else:
                        console.print(
                            f"[bold red]Error:[/] LLM provider at [cyan]{config.llm_base_url}[/] is not reachable. "
                            "Check your config or use [cyan]--no-llm[/] for transcript only."
                        )
                    raise SystemExit(1)

                if not check_llm_model_available(config):
                    if config.llm_provider == "ollama":
                        console.print(
                            f"[bold red]Error:[/] Model '{config.llm_model}' not found. "
                            f"Pull it with [cyan]ollama pull {config.llm_model}[/]"
                        )
                    else:
                        console.print(
                            f"[bold red]Error:[/] Model '{config.llm_model}' not found "
                            f"at [cyan]{config.llm_base_url}[/]."
                        )
                    raise SystemExit(1)

                def llm_callback(current: int, total: int) -> None:
                    progress.update(
                        main_task,
                        description=f"LLM extraction (chunk {current}/{total})...",
                    )

                extraction = extract_from_transcript(
                    transcript.segments, config, progress_callback=llm_callback,
                )
                console.print(
                    f"  Extracted: [cyan]{len(extraction.topics)}[/] topics, "
                    f"[cyan]{len(extraction.decisions)}[/] decisions, "
                    f"[cyan]{len(extraction.action_items)}[/] action items, "
                    f"[cyan]{len(extraction.questions)}[/] questions"
                )
            else:
                console.print("  [dim]LLM extraction skipped (--no-llm)[/]")

            # Step 7: Render Markdown
            progress.update(main_task, description="Generating Markdown output...")
            content = render(
                source_file=file_path,
                duration=duration,
                transcript=transcript,
                extraction=extraction,
                quality_flags=quality_flags,
                config=config,
            )

            # Step 8: Write output
            sidecar = build_sidecar_dict(
                source_file=file_path,
                duration=duration,
                transcript=transcript,
                extraction=extraction,
                quality_flags=quality_flags,
                config=config,
            )
            output_path = write_output(content, output_dir)

            # Step 9: Save to database
            progress.update(main_task, description="Saving to database...")
            from api.db import MeetingRepository, create_db_engine, init_db

            engine = create_db_engine(config.database_url)
            init_db(engine)
            repo = MeetingRepository(engine)
            sidecar.setdefault("filename", output_path.name)
            if not repo.meeting_exists(sidecar["filename"]):
                repo.save_meeting(sidecar, content)
                console.print("  Saved to database")
            else:
                console.print("  [dim]Already in database, skipped[/]")

            progress.update(main_task, description="[bold green]Complete!")

    return output_path
