"""LLM prompt templates for meeting note extraction."""

EXTRACTION_SCHEMA = """\
Return a JSON object with exactly these keys:

- "overview": str (2-3 sentence summary of the entire meeting — its purpose, main themes, and key outcomes)
- "topics": list of {{"title": str, "key_points": [str] (2-5 bullet points summarizing the discussion flow, attributing key arguments to speakers), "speakers": [str], "first_mentioned": "MM:SS"}}
- "decisions": list of {{"decision": str, "speaker": str, "timestamp": "MM:SS"}}
- "action_items": list of {{"task": str, "speaker": str, "deadline": str or null, "timestamp": "MM:SS"}}
- "questions": list of {{"question": str, "asker": str, "timestamp": "MM:SS", "answer": str or null, "answerer": str or null, "answer_timestamp": "MM:SS" or null}}
- "keywords": list of str (10-20 key terms and phrases from the meeting)"""

DEFAULT_INSTRUCTIONS = """\
You are analyzing a meeting transcript. Extract structured information as JSON.
Only extract what is explicitly stated in the transcript. Do not infer or hallucinate.

Rules:
- Start with "overview": a concise 2-3 sentence summary of what the meeting was about, its purpose, and key outcomes
- Consolidate related discussion into 5-8 broad themes for "topics" — do NOT create many narrow micro-topics. Group related subjects together under one clear title
- Each topic must have "key_points": 2-5 narrative bullet points that capture the discussion flow. Attribute key arguments and proposals to speakers (e.g., "Speaker 2 proposed using a business credit card to track shared expenses"). Include outcomes or conclusions where applicable
- Action items must be clear, standalone sentences that someone who wasn't in the meeting could understand (e.g., "Create a one-page website to establish company presence" NOT "Put it on there")
- For questions, search for answers within 2 minutes after the question was asked. If not answered within 2 minutes, set answer to null
- Extract 10-20 "keywords": the most important terms and phrases discussed (e.g., company names, technologies, key concepts)
- Use speaker labels exactly as they appear (e.g., "Speaker 1")
- Use MM:SS format for all timestamps
- Include ALL decisions, action items, and questions found — don't skip any

Return ONLY valid JSON, no explanation or markdown fences."""


def build_extraction_prompt(transcript_chunk: str, prompt_text: str | None = None) -> str:
    """Build the final prompt by assembling transcript + schema + instructions.

    The transcript and schema are always auto-injected. The user's template
    (or DEFAULT_INSTRUCTIONS) only needs to contain instructions — no
    placeholders required.
    """
    instructions = prompt_text if prompt_text is not None else DEFAULT_INSTRUCTIONS
    return f"TRANSCRIPT:\n{transcript_chunk}\n\n{EXTRACTION_SCHEMA}\n\n{instructions}"


def format_transcript_for_llm(segments: list) -> str:
    """Format transcript segments into readable text for the LLM."""
    lines = []
    for seg in segments:
        m, s = divmod(int(seg.start), 60)
        timestamp = f"{m:02d}:{s:02d}"
        lines.append(f"[{timestamp}] {seg.speaker}: {seg.text}")
    return "\n".join(lines)
