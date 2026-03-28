export interface Job {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: string;
  source_filename: string;
  error?: string;
}

export interface NoteSummary {
  filename: string;
  meeting_date: string;
  meeting_time: string;
  duration: string;
  speakers: number;
  topic_count: number;
  action_item_count: number;
}

export interface NoteMetadata {
  meeting_date: string;
  meeting_time: string;
  duration: string;
  speakers: number;
  source_file: string;
  model: string;
}

export interface NoteSummaryCount {
  topic_count: number;
  decision_count: number;
  action_item_count: number;
  question_count: number;
}

export interface Topic {
  title: string;
  description: string;
  key_points?: string[];
}

export interface Decision {
  decision: string;
  detail: string;
}

export interface ActionItem {
  task: string;
  detail: string;
}

export interface Question {
  question: string;
  attribution: string;
  answer: string | null;
  answer_attribution: string | null;
}

export interface TranscriptSegment {
  timestamp: string;
  speaker: string;
  text: string;
}

export interface MeetingNotes {
  filename: string;
  job_id?: string | null;
  metadata: NoteMetadata;
  summary: NoteSummaryCount;
  overview?: string;
  keywords?: string[];
  topics: Topic[];
  decisions: Decision[];
  action_items: ActionItem[];
  questions: Question[];
  transcript?: TranscriptSegment[];
  speaker_names?: SpeakerNameMap;
}

export type SpeakerNameMap = Record<string, string>;

export type AppState = 'home' | 'uploading' | 'viewing' | 'error';

export interface TemplateSummary {
  id: number;
  name: string;
  description: string;
  is_default: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateDetail extends TemplateSummary {
  prompt_text: string;
  schema: string;
}
