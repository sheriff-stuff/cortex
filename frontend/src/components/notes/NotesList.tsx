import { useCallback, useEffect, useRef, useState } from 'react';
import type { Job, NoteSummary } from '@/types';
import { api } from '@/api';
import { formatMeetingDate, estimateProgress } from '@/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { FileText, Loader2 } from 'lucide-react';

interface Props {
  onSelect: (filename: string) => void;
  onUpload: () => void;
}

export default function NotesList({ onSelect, onUpload }: Props) {
  const [notes, setNotes] = useState<NoteSummary[]>([]);
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const eventSourcesRef = useRef<Map<string, EventSource>>(new Map());
  const discoveryRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanupJob = useCallback((jobId: string) => {
    const es = eventSourcesRef.current.get(jobId);
    if (es) {
      es.close();
      eventSourcesRef.current.delete(jobId);
    }
    setActiveJobs(prev => prev.filter(j => j.job_id !== jobId));
  }, []);

  const connectJobSSE = useCallback((jobId: string) => {
    if (eventSourcesRef.current.has(jobId)) return;

    const es = new EventSource(`/jobs/${jobId}/events`);
    eventSourcesRef.current.set(jobId, es);

    es.addEventListener('progress', (e: MessageEvent) => {
      setActiveJobs(prev => prev.map(j =>
        j.job_id === jobId ? { ...j, progress: e.data } : j
      ));
    });

    es.addEventListener('done', async () => {
      cleanupJob(jobId);
      try {
        const notesList = await api.listNotes();
        setNotes(notesList);
      } catch {
        // Refresh failed — will pick up on next mount
      }
    });

    es.onerror = () => {
      cleanupJob(jobId);
    };
  }, [cleanupJob]);

  // Fetch notes and active jobs on mount, open SSE for each active job
  useEffect(() => {
    Promise.all([api.listNotes(), api.listJobs()])
      .then(([notesList, jobsList]) => {
        setNotes(notesList);
        setActiveJobs(jobsList);
        jobsList.forEach(j => connectJobSSE(j.job_id));
        setLoading(false);
      })
      .catch(() => setLoading(false));

    return () => {
      eventSourcesRef.current.forEach(es => es.close());
      eventSourcesRef.current.clear();
    };
  }, [connectJobSSE]);

  // Slow poll to discover new jobs (e.g. started from another tab)
  useEffect(() => {
    discoveryRef.current = setInterval(async () => {
      try {
        const jobs = await api.listJobs();
        for (const job of jobs) {
          if (!eventSourcesRef.current.has(job.job_id)) {
            setActiveJobs(prev => {
              if (prev.some(j => j.job_id === job.job_id)) return prev;
              return [...prev, job];
            });
            connectJobSSE(job.job_id);
          }
        }
      } catch {
        // Discovery poll failed — ignore transient errors
      }
    }, 10000);

    return () => {
      if (discoveryRef.current) {
        clearInterval(discoveryRef.current);
        discoveryRef.current = null;
      }
    };
  }, [connectJobSSE]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Notes</h1>
        <Button onClick={onUpload}>+ Process New Recording</Button>
      </div>

      {loading && <div className="text-center py-16 text-muted-foreground">Loading...</div>}

      {!loading && activeJobs.length > 0 && (
        <div className="grid gap-3 mb-4">
          {activeJobs.map((job) => {
            const pct = estimateProgress(job.progress);
            return (
              <Card key={job.job_id} className="border-primary/30 bg-primary/[0.03]">
                <CardContent>
                  <div className="flex items-center gap-3 mb-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />
                    <span className="text-[15px] font-medium">
                      Processing: {job.source_filename}
                    </span>
                    <span className="ml-auto text-xs text-muted-foreground">{pct}%</span>
                  </div>
                  <Progress value={pct} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1.5">{job.progress}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {!loading && notes.length === 0 && activeJobs.length === 0 && (
        <div className="text-center py-16">
          <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-lg text-muted-foreground">No notes yet.</p>
          <p className="text-muted-foreground">Upload a recording to get started.</p>
        </div>
      )}

      {!loading && notes.length > 0 && (
        <div className="grid gap-3">
          {notes.map((n) => (
            <Card
              key={n.filename}
              className="cursor-pointer transition-all hover:ring-2 hover:ring-primary/30 hover:shadow-md"
              role="button"
              tabIndex={0}
              onClick={() => onSelect(n.filename)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(n.filename); } }}
            >
              <CardContent>
                <div className="flex justify-between items-baseline gap-3">
                  <span className="text-[17px] font-semibold">
                    {n.title || formatMeetingDate(n.meeting_date, n.meeting_time)}
                  </span>
                  <span className="text-sm text-muted-foreground">{n.duration}</span>
                </div>
                {n.title && (
                  <div className="text-sm text-muted-foreground mt-0.5">
                    {formatMeetingDate(n.meeting_date, n.meeting_time)}
                  </div>
                )}
                <div className="flex gap-4 mt-1.5 text-[13px] text-muted-foreground">
                  <span>{n.speakers} speaker{n.speakers !== 1 ? 's' : ''}</span>
                  <span>{n.topic_count} topic{n.topic_count !== 1 ? 's' : ''}</span>
                  <span>{n.action_item_count} action item{n.action_item_count !== 1 ? 's' : ''}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
