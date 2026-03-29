"""Tests for benchmark module: StageTimer and report formatting."""

import json
import time

from api.benchmark import StageTimer, format_report_markdown, format_report_text


class TestStageTimer:
    def test_single_stage(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("step_a"):
            pass
        timer.root.end = time.perf_counter()

        result = timer.to_dict()
        assert result["name"] == "pipeline"
        assert len(result["children"]) == 1
        assert result["children"][0]["name"] == "step_a"
        assert result["children"][0]["elapsed_seconds"] >= 0

    def test_nested_stages(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("parent"):
            with timer.stage("child_1"):
                pass
            with timer.stage("child_2"):
                pass
        timer.root.end = time.perf_counter()

        result = timer.to_dict()
        parent = result["children"][0]
        assert parent["name"] == "parent"
        assert len(parent["children"]) == 2
        assert parent["children"][0]["name"] == "child_1"
        assert parent["children"][1]["name"] == "child_2"

    def test_deeply_nested(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("a"):
            with timer.stage("b"):
                with timer.stage("c"):
                    pass
        timer.root.end = time.perf_counter()

        result = timer.to_dict()
        c = result["children"][0]["children"][0]["children"][0]
        assert c["name"] == "c"

    def test_metadata_included(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("step", model="large-v3", device="cuda"):
            pass
        timer.root.end = time.perf_counter()

        result = timer.to_dict()
        child = result["children"][0]
        assert child["metadata"]["model"] == "large-v3"
        assert child["metadata"]["device"] == "cuda"

    def test_metadata_omitted_when_empty(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("step"):
            pass
        timer.root.end = time.perf_counter()

        result = timer.to_dict()
        assert "metadata" not in result["children"][0]

    def test_timing_accuracy(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("sleep"):
            time.sleep(0.05)
        timer.root.end = time.perf_counter()

        result = timer.to_dict()
        elapsed = result["children"][0]["elapsed_seconds"]
        assert elapsed >= 0.04  # allow small timing variance

    def test_to_dict_is_json_serializable(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("a", key="value"):
            with timer.stage("b"):
                pass
        timer.root.end = time.perf_counter()

        # Should not raise
        json_str = json.dumps(timer.to_dict())
        parsed = json.loads(json_str)
        assert parsed["children"][0]["name"] == "a"

    def test_multiple_sequential_stages(self):
        timer = StageTimer()
        timer.root.start = time.perf_counter()
        with timer.stage("first"):
            pass
        with timer.stage("second"):
            pass
        with timer.stage("third"):
            pass
        timer.root.end = time.perf_counter()

        result = timer.to_dict()
        assert len(result["children"]) == 3
        names = [c["name"] for c in result["children"]]
        assert names == ["first", "second", "third"]


class TestFormatReportText:
    def _make_report(self, **overrides):
        """Build a minimal valid report dict."""
        report = {
            "system": {
                "os": "Windows 11",
                "python": "3.10.0",
                "cpu": "AMD Ryzen",
                "torch": "2.0",
                "whisperx": "3.8",
            },
            "input": {
                "file": "test.mp4",
                "format": "video",
                "duration_seconds": 120,
                "duration_formatted": "2m 0s",
                "file_size_mb": 50.0,
                "wav_size_mb": 30.0,
            },
            "config": {
                "whisper_model": "large-v3",
                "whisper_device": "cuda",
                "whisper_compute_type": "float16",
                "llm_model": "qwen2.5-coder:32b",
                "chunk_max_tokens": 3000,
                "chunk_overlap_seconds": 120,
            },
            "timing": {
                "name": "pipeline",
                "elapsed_seconds": 10.0,
                "children": [
                    {"name": "validate_input", "elapsed_seconds": 0.01},
                    {"name": "transcription", "elapsed_seconds": 8.0, "children": [
                        {"name": "load_model", "elapsed_seconds": 3.0},
                        {"name": "transcribe", "elapsed_seconds": 5.0},
                    ]},
                    {"name": "quality_analysis", "elapsed_seconds": 0.01},
                ],
            },
            "transcript": {
                "segment_count": 100,
                "speaker_count": 3,
                "word_count": 5000,
                "language": "en",
            },
            "extraction": {},
            "llm": {},
            "quality": {},
            "memory": {
                "process_rss_start_mb": 200,
                "process_rss_after_transcription_mb": 3000,
                "process_rss_end_mb": 2500,
                "gpu_peak_after_transcription_mb": 0,
            },
            "output": {
                "markdown_path": "test.md",
                "markdown_size_bytes": 1000,
            },
        }
        report.update(overrides)
        return report

    def test_contains_header(self):
        text = format_report_text(self._make_report())
        assert "PIPELINE BENCHMARK REPORT" in text

    def test_contains_system_info(self):
        text = format_report_text(self._make_report())
        assert "Windows 11" in text
        assert "3.10.0" in text

    def test_contains_input_info(self):
        text = format_report_text(self._make_report())
        assert "test.mp4" in text
        assert "2m 0s" in text

    def test_contains_timing_stages(self):
        text = format_report_text(self._make_report())
        assert "validate_input" in text
        assert "transcription" in text
        assert "load_model" in text

    def test_contains_transcript_stats(self):
        text = format_report_text(self._make_report())
        assert "100" in text  # segment count
        assert "5,000" in text  # word count with comma

    def test_contains_memory_info(self):
        text = format_report_text(self._make_report())
        assert "200 MB" in text
        assert "3000 MB" in text

    def test_contains_speed(self):
        text = format_report_text(self._make_report())
        assert "realtime" in text

    def test_extraction_stats_shown_when_present(self):
        report = self._make_report(extraction={
            "topic_count": 5,
            "decision_count": 3,
            "action_item_count": 7,
            "question_count": 2,
            "keyword_count": 10,
        })
        text = format_report_text(report)
        assert "Extraction Results" in text
        assert "Topics:" in text

    def test_extraction_stats_hidden_when_empty(self):
        text = format_report_text(self._make_report())
        assert "Extraction Results" not in text

    def test_gpu_shown_when_present(self):
        report = self._make_report()
        report["system"]["gpu_name"] = "RTX 4090"
        report["system"]["gpu_memory_gb"] = 24
        report["memory"]["gpu_peak_after_transcription_mb"] = 8000
        text = format_report_text(report)
        assert "RTX 4090" in text
        assert "8000 MB" in text

    def test_quality_flags_shown(self):
        report = self._make_report(quality={
            "total_flags": 2,
            "by_type": {"low_confidence": 1, "long_silence": 1},
        })
        text = format_report_text(report)
        assert "Quality Flags" in text
        assert "low_confidence" in text


class TestFormatReportMarkdown:
    def _make_report(self, **overrides):
        """Build a minimal valid report dict."""
        report = {
            "system": {
                "os": "Windows 11",
                "python": "3.10.0",
                "cpu": "AMD Ryzen",
                "torch": "2.0",
                "whisperx": "3.8",
            },
            "input": {
                "file": "test.mp4",
                "format": "video",
                "duration_seconds": 120,
                "duration_formatted": "2m 0s",
                "file_size_mb": 50.0,
                "wav_size_mb": 30.0,
            },
            "config": {
                "whisper_model": "large-v3",
                "whisper_device": "cuda",
                "whisper_compute_type": "float16",
                "llm_model": "qwen2.5-coder:32b",
                "chunk_max_tokens": 3000,
                "chunk_overlap_seconds": 120,
            },
            "timing": {
                "name": "pipeline",
                "elapsed_seconds": 10.0,
                "children": [
                    {"name": "validate_input", "elapsed_seconds": 0.01},
                    {"name": "transcription", "elapsed_seconds": 8.0, "children": [
                        {"name": "load_model", "elapsed_seconds": 3.0},
                        {"name": "transcribe", "elapsed_seconds": 5.0},
                    ]},
                ],
            },
            "transcript": {
                "segment_count": 100,
                "speaker_count": 3,
                "word_count": 5000,
                "language": "en",
            },
            "extraction": {},
            "llm": {},
            "quality": {},
            "memory": {
                "process_rss_start_mb": 200,
                "process_rss_after_transcription_mb": 3000,
                "process_rss_end_mb": 2500,
                "gpu_peak_after_transcription_mb": 0,
            },
            "output": {
                "markdown_path": "test.md",
                "markdown_size_bytes": 1000,
            },
        }
        report.update(overrides)
        return report

    def test_starts_with_h1(self):
        md = format_report_markdown(self._make_report())
        assert md.startswith("# Pipeline Benchmark Report")

    def test_has_markdown_tables(self):
        md = format_report_markdown(self._make_report())
        assert "|----------|-------|" in md  # table separator

    def test_has_stage_timing_table(self):
        md = format_report_markdown(self._make_report())
        assert "## Stage Timing" in md
        assert "| validate_input |" in md
        assert "| **TOTAL** |" in md

    def test_nested_stages_indented(self):
        md = format_report_markdown(self._make_report())
        # Child stages should have non-breaking space indentation
        assert "load_model" in md
        assert "transcribe" in md

    def test_contains_all_sections(self):
        md = format_report_markdown(self._make_report())
        assert "## System" in md
        assert "## Input" in md
        assert "## Config" in md
        assert "## Stage Timing" in md
        assert "## Transcript" in md
        assert "## Memory" in md

    def test_extraction_section_when_present(self):
        report = self._make_report(extraction={
            "topic_count": 5,
            "decision_count": 3,
            "action_item_count": 7,
            "question_count": 2,
            "keyword_count": 10,
        })
        md = format_report_markdown(report)
        assert "## Extraction Results" in md
        assert "| Topics | 5 |" in md

    def test_performance_section(self):
        md = format_report_markdown(self._make_report())
        assert "## Performance" in md
        assert "realtime" in md

    def test_llm_section_with_per_chunk_details(self):
        report = self._make_report(llm={
            "chunk_count": 2,
            "estimated_tokens_per_chunk": [3000, 2800],
            "prompt_sizes_chars": [8000, 7500],
        })
        md = format_report_markdown(report)
        assert "## LLM Extraction" in md
        assert "Chunk 1" in md
        assert "Chunk 2" in md
