# Local AI Meeting Notes System - Requirements Document

## What I Want to Build

A local AI tool that takes recorded meeting files and produces structured notes with:

- Full transcript with speaker labels (Speaker 1, Speaker 2, etc.)
- Summary of key topics discussed
- Decisions that were made
- Action items and commitments
- Questions that were asked (with answers if they were given)

## Key Principles

- Everything runs locally - no cloud services
- Quality matters more than speed
- Simple CLI workflow
- Output as readable Markdown files

---

## MVP Scope

### What It Does

- Takes a recorded meeting file (audio or video)
- Transcribes it with speaker labels (Speaker 1, Speaker 2, etc.)
- Extracts:
  - Key topics discussed
  - Decisions made
  - Action items (any future-oriented statement like "I'll...", "we need to...")
  - Questions (with answers if they were given)
- Outputs a Markdown file with full transcript + structured summary
- CLI tool: `meeting-notes process <file>`

### What It Doesn't Do (Yet)

- Live meeting capture
- Identify speakers by name
- GUI
- Integration with other tools

---

## Technical Approach

Use local AI models for everything:

- Speech-to-text with speaker diarization
- LLM via Ollama for summarization and extraction
- Process: audio file → transcript → structured summary → Markdown

---

## What It Needs to Do

### 1. Accept Input

- Audio files: MP3, WAV, M4A, AAC
- Video files: MP4, MKV, AVI, MOV
- Extract audio from video if needed

### 2. Transcribe

- Convert speech to text
- Identify different speakers (Speaker 1, Speaker 2, etc.)
- Include timestamps

### 3. Extract Structure

Use an LLM to pull out:

- **Topics**: Main things discussed
- **Decisions**: What was decided
- **Action Items**: Any future-oriented statements ("I'll...", "we need to...", "let's...")
- **Questions & Answers**:
  - Find all questions
  - If answered within ~2 minutes, include the answer
  - If not answered, flag it

### 4. Output

Generate a Markdown file with:

- YAML frontmatter (date, duration, speakers, source file)
- Structured summary sections
- Full transcript with speaker labels and timestamps
- Save to a directory the user specifies

### 5. Handle Issues

- Flag sections with poor audio quality
- Flag uncertainties in transcription
- Show clear error messages if something fails

---

## How It Works

1. Record a meeting (however you normally do that)
2. Run: `meeting-notes process recording.mp4 --output-dir ~/meeting-notes/`
3. Wait a few minutes while it processes
4. Get a Markdown file with full transcript + structured summary

## LLM Extraction Guidance

The LLM should analyze the transcript and extract structured information. Key principles:

- Only extract what's explicitly in the transcript
- Don't hallucinate or infer
- Include speaker labels and timestamps
- For questions: look for answers within ~2 minutes
- For action items: catch any future-oriented language ("I'll", "we need to", "let's", etc.)

## Success Criteria

The MVP is done when:

- It can process common audio/video formats
- Transcripts are accurate for clear audio
- Speakers are separated and labeled
- Action items, decisions, and questions are extracted
- Questions + answers are matched correctly
- Output is a readable Markdown file
- CLI works reliably
- Errors are clear and helpful

---

## Appendix: Example Output

### Sample Markdown Output

```markdown
---
meeting_date: 2026-03-23
meeting_time: 14:30
duration: 45m 32s
speakers: 3
audio_file: /home/ben/Downloads/client-call-2026-03-23.mp4
processing_date: 2026-03-23T15:15:00
whisper_model: large-v3
llm_model: qwen2.5:32b
quality_flags:
  - type: overlapping_speech
    timestamp: "22:10-22:18"
    description: "Multiple speakers talking simultaneously"
---

# Meeting Summary - Client Call - 2026-03-23

**Duration**: 45 minutes 32 seconds  
**Speakers**: 3  
**Date**: March 23, 2026 at 14:30

## Key Topics Discussed

1. **Authentication Flow Requirements** - Discussion of OAuth vs. SAML for enterprise SSO
2. **Database Schema Design** - Choosing between PostgreSQL and MySQL for JSON support
3. **Deployment Timeline** - Target dates for staging and production releases
4. **Security Compliance** - GDPR and SOC2 requirements for UK customers

## Decisions Made

- ✅ **Use PostgreSQL** - Decided to go with PostgreSQL for better JSON support and full-text search (Speaker 1, 14:35)
- ✅ **OAuth 2.0 with PKCE** - Client agreed to OAuth over SAML for better mobile support (Speaker 2, 18:45)
- ✅ **Staging deploy March 30** - Target staging deployment for end of month (Speaker 1, 32:10)

## Action Items

- [ ] **Set up PostgreSQL database schema** - Speaker 1, by Friday (32:15)
- [ ] **Draft OAuth integration guide** - Speaker 3, by next Tuesday (35:40)
- [ ] **Schedule follow-up with security team** - Speaker 2, this week (40:22)
- [ ] **Prepare staging environment** - Speaker 1, by March 28 (42:10)
- [ ] **Share GDPR compliance checklist** - Speaker 2, by Monday (43:55)

## Questions & Answers

### ❓ Should we use PostgreSQL or MySQL for the backend? (Speaker 2, 14:32)

**✅ Answer**: Let's go with PostgreSQL for JSON support and better full-text search capabilities. (Speaker 1, 14:35)

### ❓ What about SAML for enterprise customers who require it? (Speaker 3, 19:20)

**✅ Answer**: We can add SAML support in Phase 2, OAuth covers 90% of use cases for now. (Speaker 1, 19:25)

### ❓ Do we need SOC2 compliance before production launch? (Speaker 2, 38:15)

**⚠️ Unanswered** - This was mentioned but not resolved in the meeting.

### ❓ Who will handle the security audit? (Speaker 3, 41:05)

**✅ Answer**: I'll coordinate with our security team and schedule it for next week. (Speaker 2, 41:10)

---

## Full Transcript

**[00:00:15] Speaker 1:**  
Alright, let's get started. Thanks for joining today. We need to finalize the database choice and talk through the authentication flow.

**[00:00:23] Speaker 2:**  
Sounds good. I've been looking at both PostgreSQL and MySQL. The JSON support in Postgres seems better for our use case.

**[00:00:32] Speaker 3:**  
Agreed. We're also storing a lot of unstructured data from the API integrations.

**[00:00:40] Speaker 1:**  
Okay, so leaning toward Postgres. Any concerns with that?

**[00:00:45] Speaker 2:**  
No major concerns. Our team has more experience with Postgres anyway.

**[00:00:52] Speaker 1:**  
Great, let's lock that in. PostgreSQL it is.

... [transcript continues] ...

**[00:45:20] Speaker 1:**  
Alright, I think we're good. I'll send out meeting notes and action items this afternoon.

**[00:45:28] Speaker 2:**  
Perfect. Talk next week.

**[00:45:32] Speaker 3:**  
Thanks everyone!

---

## Quality Notes

⚠️ **Overlapping Speech Detected**: 22:10-22:18 - Multiple speakers talking simultaneously, transcription may be incomplete in this section.

✅ **Audio Quality**: Overall good, clear speech from all participants.

---

_Generated by meeting-notes v1.0.0 on 2026-03-23 at 15:15_  
_Processing time: 8m 05s_
```
