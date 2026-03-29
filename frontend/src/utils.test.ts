import type { MeetingNotes } from '@/types';
import {
  ACCEPTED_EXTENSIONS,
  applySpeakerNames,
  estimateProgress,
  extractSpeakers,
  formatFileSize,
  formatMeetingDate,
  isValidFile,
} from '@/utils';

interface MeetingNotesOverrides {
  metadata?: Partial<MeetingNotes['metadata']>;
  summary?: Partial<MeetingNotes['summary']>;
  topics?: MeetingNotes['topics'];
  decisions?: MeetingNotes['decisions'];
  action_items?: MeetingNotes['action_items'];
  questions?: MeetingNotes['questions'];
}

function makeMeetingNotes(overrides: MeetingNotesOverrides = {}): MeetingNotes {
  return {
    filename: 'test.md',
    metadata: {
      meeting_date: '2025-01-15',
      meeting_time: '10:00 AM',
      duration: '30m',
      speakers: 0,
      source_file: 'test.mp3',
      model: 'test',
      ...overrides.metadata,
    },
    summary: {
      topic_count: 0,
      decision_count: 0,
      action_item_count: 0,
      question_count: 0,
      ...overrides.summary,
    },
    topics: overrides.topics ?? [],
    decisions: overrides.decisions ?? [],
    action_items: overrides.action_items ?? [],
    questions: overrides.questions ?? [],
  };
}

// --- extractSpeakers ---

describe('extractSpeakers', () => {
  it('extracts speakers from topic descriptions', () => {
    const notes = makeMeetingNotes({
      topics: [
        { title: 'Intro', description: 'Speaker 1 introduced the topic. Speaker 2 agreed.' },
      ],
    });
    expect(extractSpeakers(notes)).toEqual(['Speaker 1', 'Speaker 2']);
  });

  it('deduplicates speakers across fields', () => {
    const notes = makeMeetingNotes({
      topics: [{ title: 'T', description: 'Speaker 1 said something' }],
      decisions: [{ decision: 'D', detail: 'Speaker 1 decided' }],
    });
    expect(extractSpeakers(notes)).toEqual(['Speaker 1']);
  });

  it('sorts numerically, not lexicographically', () => {
    const notes = makeMeetingNotes({
      topics: [
        { title: 'T', description: 'Speaker 10 and Speaker 2 and Speaker 1' },
      ],
    });
    expect(extractSpeakers(notes)).toEqual(['Speaker 1', 'Speaker 2', 'Speaker 10']);
  });

  it('backfills from metadata.speakers count', () => {
    const notes = makeMeetingNotes({
      metadata: { speakers: 3 },
      topics: [{ title: 'T', description: 'Speaker 1 spoke' }],
    });
    const result = extractSpeakers(notes);
    expect(result).toEqual(['Speaker 1', 'Speaker 2', 'Speaker 3']);
  });

  it('returns empty array when no speakers exist', () => {
    const notes = makeMeetingNotes();
    expect(extractSpeakers(notes)).toEqual([]);
  });

  it('extracts multi-digit speaker numbers', () => {
    const notes = makeMeetingNotes({
      topics: [{ title: 'T', description: 'Speaker 12 presented' }],
    });
    expect(extractSpeakers(notes)).toEqual(['Speaker 12']);
  });

  it('collects speakers from all four field types', () => {
    const notes = makeMeetingNotes({
      topics: [{ title: 'T', description: 'Speaker 1 topic' }],
      decisions: [{ decision: 'D', detail: 'Speaker 2 decided' }],
      action_items: [{ task: 'A', detail: 'Speaker 3 will do it' }],
      questions: [{ question: 'Q', attribution: 'Speaker 4', answer: null, answer_attribution: null }],
    });
    expect(extractSpeakers(notes)).toEqual(['Speaker 1', 'Speaker 2', 'Speaker 3', 'Speaker 4']);
  });
});

// --- applySpeakerNames ---

describe('applySpeakerNames', () => {
  it('replaces a single speaker label', () => {
    expect(applySpeakerNames('Speaker 1 said hi', { 'Speaker 1': 'Alice' })).toBe('Alice said hi');
  });

  it('replaces multiple speaker labels', () => {
    const result = applySpeakerNames('Speaker 1 and Speaker 2', {
      'Speaker 1': 'Alice',
      'Speaker 2': 'Bob',
    });
    expect(result).toBe('Alice and Bob');
  });

  it('skips empty names', () => {
    expect(applySpeakerNames('Speaker 1 said hi', { 'Speaker 1': '' })).toBe('Speaker 1 said hi');
  });

  it('returns empty string for empty input', () => {
    expect(applySpeakerNames('', { 'Speaker 1': 'Alice' })).toBe('');
  });

  it('leaves text unchanged when no labels match', () => {
    expect(applySpeakerNames('No speakers here', { 'Speaker 1': 'Alice' })).toBe('No speakers here');
  });

  it('replaces all occurrences of the same label', () => {
    expect(applySpeakerNames('Speaker 1 and Speaker 1', { 'Speaker 1': 'Alice' })).toBe(
      'Alice and Alice',
    );
  });

  it('handles overlapping speaker labels like "Speaker 1" and "Speaker 10"', () => {
    const result = applySpeakerNames('Speaker 1 then Speaker 10 and Speaker 1 again', {
      'Speaker 1': 'Alice',
      'Speaker 10': 'Bob',
    });
    expect(result).toBe('Alice then Bob and Alice again');
  });
});

// --- formatMeetingDate ---

describe('formatMeetingDate', () => {
  it('formats date only', () => {
    expect(formatMeetingDate('2025-01-15')).toBe('Wed, January 15, 2025');
  });

  it('formats date with time', () => {
    expect(formatMeetingDate('2025-01-15', '2:30 PM')).toBe('Wed, January 15, 2025 at 2:30 PM');
  });

  it('formats a different month', () => {
    expect(formatMeetingDate('2025-06-01')).toBe('Sun, June 1, 2025');
  });
});

// --- formatFileSize ---

describe('formatFileSize', () => {
  it('formats zero bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('formats bytes range', () => {
    expect(formatFileSize(512)).toBe('512 B');
  });

  it('formats boundary at 1023 bytes', () => {
    expect(formatFileSize(1023)).toBe('1023 B');
  });

  it('formats exact KB', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
  });

  it('formats fractional KB', () => {
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('formats exact MB', () => {
    expect(formatFileSize(1048576)).toBe('1.0 MB');
  });
});

// --- isValidFile ---

describe('isValidFile', () => {
  it.each(ACCEPTED_EXTENSIONS)('accepts %s files', (ext) => {
    const file = new File([], `recording${ext}`);
    expect(isValidFile(file)).toBe(true);
  });

  it.each(['.txt', '.pdf', '.exe'])('rejects %s files', (ext) => {
    const file = new File([], `file${ext}`);
    expect(isValidFile(file)).toBe(false);
  });

  it('handles uppercase extensions', () => {
    const file = new File([], 'RECORDING.MP3');
    expect(isValidFile(file)).toBe(true);
  });

  it('rejects files with no extension', () => {
    const file = new File([], 'noext');
    expect(isValidFile(file)).toBe(false);
  });
});

// --- estimateProgress ---

describe('estimateProgress', () => {
  it.each([
    ['Validating file', 3],
    ['Reading file', 5],
    ['Extracting audio', 8],
    ['Preparing audio', 8],
    ['Loading whisper model', 12],
    ['Voice activity detection', 16],
    ['Transcribing audio', 25],
    ['Aligning transcript', 35],
    ['Identifying speakers', 42],
    ['Diarization in progress', 42],
    ['Quality check', 47],
    ['Saving transcript', 50],
    ['Checking ollama', 52],
    ['LLM extraction', 60],
    ['Ollama not available', 100],
    ['Summary skipped', 100],
    ['Generating summary', 92],
    ['Saving notes', 96],
    ['Complete', 100],
  ] as const)('maps "%s" to %d%%', (progress, expected) => {
    expect(estimateProgress(progress)).toBe(expected);
  });

  it('parses LLM extraction chunk progress', () => {
    expect(estimateProgress('LLM extraction chunk 2/4')).toBe(73);
    expect(estimateProgress('LLM extraction chunk 1/4')).toBe(64);
    expect(estimateProgress('LLM extraction chunk 4/4')).toBe(90);
  });

  it('is case insensitive', () => {
    expect(estimateProgress('TRANSCRIBING AUDIO')).toBe(25);
    expect(estimateProgress('complete')).toBe(100);
  });

  it('returns 5 for unknown progress strings', () => {
    expect(estimateProgress('something unknown')).toBe(5);
  });
});

// --- ACCEPTED_EXTENSIONS ---

describe('ACCEPTED_EXTENSIONS', () => {
  it('contains the expected extensions', () => {
    expect(ACCEPTED_EXTENSIONS).toEqual(['.mp3', '.wav', '.m4a', '.aac', '.mp4', '.mkv', '.avi', '.mov']);
  });
});
