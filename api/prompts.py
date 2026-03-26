"""LLM prompt templates for meeting note extraction."""

EXTRACTION_PROMPT = """\
You are analyzing a meeting transcript. Extract structured information as JSON.
Only extract what is explicitly stated in the transcript. Do not infer or hallucinate.

TRANSCRIPT:
{transcript_chunk}

Return a JSON object with exactly these keys:

- "topics": list of {{"title": str, "description": str (1 sentence), "speakers": [str], "first_mentioned": "MM:SS"}}
- "decisions": list of {{"decision": str, "speaker": str, "timestamp": "MM:SS"}}
- "action_items": list of {{"task": str, "speaker": str, "deadline": str or null, "timestamp": "MM:SS"}}
- "questions": list of {{"question": str, "asker": str, "timestamp": "MM:SS", "answer": str or null, "answerer": str or null, "answer_timestamp": "MM:SS" or null}}

Rules:
- For action items, look for future-oriented language: "I'll", "we need to", "let's", "will", "should", "going to"
- For questions, search for answers within 2 minutes after the question was asked
- If a question was not answered within 2 minutes, set answer to null
- Use speaker labels exactly as they appear (e.g., "Speaker 1")
- Use MM:SS format for all timestamps
- Include ALL items found, don't skip any

Return ONLY valid JSON, no explanation or markdown fences."""


def build_extraction_prompt(transcript_chunk: str) -> str:
    """Build the extraction prompt for a transcript chunk."""
    return EXTRACTION_PROMPT.format(transcript_chunk=transcript_chunk)


def format_transcript_for_llm(segments: list) -> str:
    """Format transcript segments into readable text for the LLM."""
    lines = []
    for seg in segments:
        m, s = divmod(int(seg.start), 60)
        timestamp = f"{m:02d}:{s:02d}"
        lines.append(f"[{timestamp}] {seg.speaker}: {seg.text}")
    return "\n".join(lines)
