import type { ActionItem, Decision, Job, MeetingNotes, NoteSummary, Question, SpeakerNameMap, TemplateDetail, TemplateSummary, Topic } from './types';

/** Shared fetch wrapper with consistent error handling. */
async function fetchApi<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function jsonBody(data: unknown): RequestInit {
  return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
}

// --- Jobs ---

async function upload(file: File, templateId?: number): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('file', file);
  if (templateId != null) form.append('template_id', String(templateId));
  return fetchApi('/jobs', { method: 'POST', body: form });
}

function getJob(jobId: string): Promise<Job> {
  return fetchApi(`/jobs/${jobId}`);
}

function listJobs(): Promise<Job[]> {
  return fetchApi('/jobs');
}

function resummarize(jobId: string, templateId?: number): Promise<{ job_id: string }> {
  const params = templateId != null ? `?template_id=${templateId}` : '';
  return fetchApi(`/jobs/${jobId}/resummarize${params}`, { method: 'POST' });
}

// --- Notes ---

function listNotes(): Promise<NoteSummary[]> {
  return fetchApi('/api/notes');
}

function getSavedNotes(filename: string): Promise<MeetingNotes> {
  return fetchApi(`/api/notes/${encodeURIComponent(filename)}`);
}

async function getSpeakers(filename: string): Promise<SpeakerNameMap> {
  const data = await fetchApi<{ speaker_names: SpeakerNameMap }>(
    `/api/notes/${encodeURIComponent(filename)}/speakers`,
  );
  return data.speaker_names;
}

async function saveSpeakers(filename: string, speakerNames: SpeakerNameMap): Promise<SpeakerNameMap> {
  const data = await fetchApi<{ speaker_names: SpeakerNameMap }>(
    `/api/notes/${encodeURIComponent(filename)}/speakers`,
    { method: 'PUT', ...jsonBody({ speaker_names: speakerNames }) },
  );
  return data.speaker_names;
}

async function updateTitle(filename: string, title: string): Promise<string> {
  const data = await fetchApi<{ title: string }>(
    `/api/notes/${encodeURIComponent(filename)}/title`,
    { method: 'PUT', ...jsonBody({ title }) },
  );
  return data.title;
}

// --- Templates ---

function listTemplates(): Promise<TemplateSummary[]> {
  return fetchApi('/api/templates');
}

function getTemplate(id: number): Promise<TemplateDetail> {
  return fetchApi(`/api/templates/${id}`);
}

function createTemplate(data: { name: string; description: string; prompt_text: string }): Promise<TemplateDetail> {
  return fetchApi('/api/templates', { method: 'POST', ...jsonBody(data) });
}

function updateTemplate(id: number, data: Partial<{ name: string; description: string; prompt_text: string }>): Promise<TemplateDetail> {
  return fetchApi(`/api/templates/${id}`, { method: 'PUT', ...jsonBody(data) });
}

function deleteTemplate(id: number): Promise<void> {
  return fetchApi(`/api/templates/${id}`, { method: 'DELETE' });
}

function duplicateTemplate(id: number): Promise<TemplateDetail> {
  return fetchApi(`/api/templates/${id}/duplicate`, { method: 'POST' });
}

function renderExample(promptText: string): Promise<{
  topics: Topic[];
  decisions: Decision[];
  action_items: ActionItem[];
  questions: Question[];
}> {
  return fetchApi('/api/templates/render-example', {
    method: 'POST',
    ...jsonBody({ prompt_text: promptText }),
  });
}

export const api = {
  upload, getJob, listJobs, listNotes, getSavedNotes, getSpeakers, saveSpeakers, updateTitle,
  listTemplates, getTemplate, createTemplate, updateTemplate, deleteTemplate, duplicateTemplate,
  renderExample, resummarize,
};
