import type { MeetingNotes, SpeakerNameMap } from '@/types';

const SPEAKER_PATTERN = /Speaker \d+/g;

export function extractSpeakers(notes: MeetingNotes): string[] {
  const found = new Set<string>();

  for (const t of notes.topics) {
    for (const m of t.description.matchAll(SPEAKER_PATTERN)) found.add(m[0]);
  }
  for (const d of notes.decisions) {
    for (const m of d.detail.matchAll(SPEAKER_PATTERN)) found.add(m[0]);
  }
  for (const a of notes.action_items) {
    for (const m of a.detail.matchAll(SPEAKER_PATTERN)) found.add(m[0]);
  }
  for (const q of notes.questions) {
    for (const m of q.attribution.matchAll(SPEAKER_PATTERN)) found.add(m[0]);
  }

  // Ensure we have at least as many entries as metadata.speakers count
  for (let i = 1; i <= notes.metadata.speakers; i++) {
    found.add(`Speaker ${i}`);
  }

  return [...found].sort((a, b) => {
    const numA = parseInt(a.replace('Speaker ', ''), 10);
    const numB = parseInt(b.replace('Speaker ', ''), 10);
    return numA - numB;
  });
}

export function applySpeakerNames(text: string, names: SpeakerNameMap): string {
  if (!text) return text;
  let result = text;
  for (const [label, name] of Object.entries(names)) {
    if (!name) continue;
    result = result.replaceAll(label, name);
  }
  return result;
}

// --- Date & file formatting ---

export function formatMeetingDate(dateStr: string, timeStr?: string): string {
  const formatted = new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  return timeStr ? `${formatted} at ${timeStr}` : formatted;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// --- File validation ---

export const ACCEPTED_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.mp4', '.mkv', '.avi', '.mov'];

export function isValidFile(file: File): boolean {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  return ACCEPTED_EXTENSIONS.includes(ext);
}

// --- Job progress estimation ---

/** Map a progress string to an estimated percentage.
 *  Phase 1 (transcription) maps to 0-50%, Phase 2 (summary) maps to 50-100%.
 */
export function estimateProgress(progress: string): number {
  const lower = progress.toLowerCase();
  // Phase 1: Transcription (0-50%)
  if (lower.includes('validat')) return 3;
  if (lower.includes('reading file')) return 5;
  if (lower.includes('extracting audio') || lower.includes('preparing audio')) return 8;
  if (lower.includes('loading whisper')) return 12;
  if (lower.includes('voice activity')) return 16;
  if (lower.includes('transcribing')) return 25;
  if (lower.includes('aligning')) return 35;
  if (lower.includes('identifying speaker') || lower.includes('diariz')) return 42;
  if (lower.includes('quality')) return 47;
  if (lower.includes('saving transcript')) return 50;
  // Phase 2: Summary (50-100%)
  if (lower.includes('checking ollama')) return 52;
  if (lower.includes('llm extraction')) {
    const match = progress.match(/chunk (\d+)\/(\d+)/);
    if (match) {
      const [, current, total] = match;
      return 55 + Math.round((parseInt(current) / parseInt(total)) * 35);
    }
    return 60;
  }
  if (lower.includes('ollama not available') || lower.includes('summary skipped')) return 100;
  if (lower.includes('generating')) return 92;
  if (lower.includes('saving')) return 96;
  if (lower.includes('complete')) return 100;
  return 5;
}
