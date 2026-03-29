export const DEFAULT_PROMPT = `You are analyzing a meeting transcript. Extract structured information as JSON.
Only extract what is explicitly stated in the transcript. Do not infer or hallucinate.

Rules:
- For action items, look for future-oriented language: "I'll", "we need to", "let's", "will", "should", "going to"
- For questions, search for answers within 2 minutes after the question was asked
- If a question was not answered within 2 minutes, set answer to null
- Use speaker labels exactly as they appear (e.g., "Speaker 1")
- Use MM:SS format for all timestamps
- Include ALL items found, don't skip any

Return ONLY valid JSON, no explanation or markdown fences.`;
