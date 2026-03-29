export const API_URL = 'http://localhost:9099';

interface SeedMeetingOptions {
  filename?: string;
  meetingDate?: string;
  meetingTime?: string;
  duration?: string;
  speakers?: number;
  overview?: string;
  topicCount?: number;
  actionItemCount?: number;
}

export async function seedMeeting(opts: SeedMeetingOptions = {}) {
  const filename = opts.filename ?? 'test-meeting-2025-01-15.json';
  const sidecar = {
    filename,
    metadata: {
      meeting_date: opts.meetingDate ?? '2025-01-15',
      meeting_time: opts.meetingTime ?? '10:00',
      duration: opts.duration ?? '45:00',
      speakers: opts.speakers ?? 3,
      audio_file: 'test-recording.mp3',
      processing_date: '2025-01-15T12:00:00Z',
      whisper_model: 'large-v3',
      llm_model: 'test-model',
    },
    summary: {
      topic_count: opts.topicCount ?? 2,
      decision_count: 1,
      action_item_count: opts.actionItemCount ?? 1,
      question_count: 1,
    },
    overview: opts.overview ?? 'Test meeting about project planning and roadmap.',
    keywords: ['planning', 'roadmap', 'testing'],
    topics: [
      { title: 'Project Roadmap', description: 'Discussed Q1 goals and milestones', key_points: ['Ship v2 by March', 'Hire two more engineers'] },
      { title: 'Testing Strategy', description: 'Agreed on E2E testing approach', key_points: ['Use Playwright', 'Cover main user flows'] },
    ],
    decisions: [
      { decision: 'Ship v2 by end of March', speaker: 'Speaker 1', timestamp: '05:30' },
    ],
    action_items: [
      { task: 'Write the technical spec', speaker: 'Speaker 2', deadline: '2025-02-01', timestamp: '10:15' },
    ],
    questions: [
      { question: 'When is the deadline?', asker: 'Speaker 3', timestamp: '08:00', answer: 'End of March', answerer: 'Speaker 1', answer_timestamp: '08:05' },
    ],
  };

  const res = await fetch(`${API_URL}/api/test/seed-meeting`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sidecar, markdown: '# Test Meeting Notes\n\nThis is test content.' }),
  });
  if (!res.ok) throw new Error(`Seed failed: ${res.status} ${await res.text()}`);
  return { filename, ...(await res.json()) };
}
