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
