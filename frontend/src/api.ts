import type { Job, MeetingNotes, NoteSummary, SpeakerNameMap } from './types';

async function upload(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/jobs', { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Failed to get job: ${res.statusText}`);
  return res.json();
}

async function listJobs(): Promise<Job[]> {
  const res = await fetch('/jobs');
  if (!res.ok) throw new Error(`Failed to list jobs: ${res.statusText}`);
  return res.json();
}

async function listNotes(): Promise<NoteSummary[]> {
  const res = await fetch('/api/notes');
  if (!res.ok) throw new Error(`Failed to list notes: ${res.statusText}`);
  return res.json();
}

async function getSavedNotes(filename: string): Promise<MeetingNotes> {
  const res = await fetch(`/api/notes/${encodeURIComponent(filename)}`);
  if (!res.ok) throw new Error(`Failed to get notes: ${res.statusText}`);
  return res.json();
}

async function getSpeakers(filename: string): Promise<SpeakerNameMap> {
  const res = await fetch(`/api/notes/${encodeURIComponent(filename)}/speakers`);
  if (!res.ok) throw new Error(`Failed to get speakers: ${res.statusText}`);
  const data = await res.json();
  return data.speaker_names;
}

async function saveSpeakers(filename: string, speakerNames: SpeakerNameMap): Promise<SpeakerNameMap> {
  const res = await fetch(`/api/notes/${encodeURIComponent(filename)}/speakers`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speaker_names: speakerNames }),
  });
  if (!res.ok) throw new Error(`Failed to save speakers: ${res.statusText}`);
  const data = await res.json();
  return data.speaker_names;
}

export const api = { upload, getJob, listJobs, listNotes, getSavedNotes, getSpeakers, saveSpeakers };
