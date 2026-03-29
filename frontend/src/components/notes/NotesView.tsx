import { useCallback, useEffect, useState } from 'react';
import type { MeetingNotes, SpeakerNameMap } from '@/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ArrowLeft, RefreshCw, Loader2 } from 'lucide-react';
import SpeakerEditor from '@/components/SpeakerEditor';
import SummaryTab from '@/components/notes/SummaryTab';
import TranscriptTab from '@/components/notes/TranscriptTab';
import { extractSpeakers, applySpeakerNames } from '@/utils';
import { usePollJob } from '@/hooks/usePollJob';
import { api } from '@/api';

interface Props {
  notes: MeetingNotes;
  onReset: () => void;
  onNotesUpdated?: (notes: MeetingNotes) => void;
}

export default function NotesView({ notes: initialNotes, onReset, onNotesUpdated }: Props) {
  const [notes, setNotes] = useState(initialNotes);
  const { metadata } = notes;
  const [speakerNames, setSpeakerNames] = useState<SpeakerNameMap>(
    () => notes.speaker_names ?? {},
  );
  const [resummarizing, setResummarizing] = useState(false);
  const [resummarizeProgress, setResummarizeProgress] = useState('');
  const speakers = extractSpeakers(notes);
  const apply = (text: string) => applySpeakerNames(text, speakerNames);

  const { startPolling } = usePollJob({
    onProgress: (job) => setResummarizeProgress(job.progress || job.status),
    onComplete: async () => {
      const updated = await api.getSavedNotes(notes.filename);
      setNotes(updated);
      setSpeakerNames(updated.speaker_names ?? {});
      onNotesUpdated?.(updated);
      setResummarizing(false);
      setResummarizeProgress('');
    },
    onFailed: () => {
      setResummarizing(false);
      setResummarizeProgress('');
    },
  });

  // Sync when parent passes new notes (e.g. navigating to a different note)
  useEffect(() => {
    setNotes(initialNotes);
    setSpeakerNames(initialNotes.speaker_names ?? {});
    setResummarizing(false);
    setResummarizeProgress('');
  }, [initialNotes.filename, initialNotes]);

  const handleSave = useCallback(
    async (names: SpeakerNameMap) => {
      setSpeakerNames(names);
      try {
        const saved = await api.saveSpeakers(notes.filename, names);
        setSpeakerNames(saved);
      } catch {
        // Keep optimistic local state — speaker names still usable if API is down
      }
    },
    [notes.filename],
  );

  const handleResummarize = useCallback(async () => {
    if (!notes.job_id) return;
    setResummarizing(true);
    setResummarizeProgress('Starting...');
    try {
      const { job_id: newJobId } = await api.resummarize(notes.job_id);
      startPolling(newJobId);
    } catch {
      // API call to start resummarize failed — reset UI state
      setResummarizing(false);
      setResummarizeProgress('');
    }
  }, [notes.job_id, startPolling]);

  const hasTranscript = notes.transcript && notes.transcript.length > 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Notes &mdash; {metadata.meeting_date}
          </h1>
          <div className="flex flex-wrap gap-2 mt-2">
            <Badge variant="secondary">Duration: {metadata.duration}</Badge>
            <Badge variant="secondary">Speakers: {metadata.speakers}</Badge>
            {metadata.meeting_time && (
              <Badge variant="secondary">Time: {metadata.meeting_time}</Badge>
            )}
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {notes.job_id && (
            <Button
              variant="outline"
              onClick={handleResummarize}
              disabled={resummarizing}
            >
              <RefreshCw className={`h-4 w-4 ${resummarizing ? 'animate-spin' : ''}`} />
              {resummarizing ? 'Resummarizing...' : 'Resummarize'}
            </Button>
          )}
          <Button variant="outline" onClick={onReset}>
            <ArrowLeft className="h-4 w-4" />
            All Notes
          </Button>
        </div>
      </div>

      {/* Speaker Editor */}
      {speakers.length > 0 && (
        <SpeakerEditor
          speakers={speakers}
          speakerNames={speakerNames}
          onSave={handleSave}
        />
      )}

      {/* Tabs */}
      <Tabs defaultValue="summary">
        <TabsList variant="line" className="w-full justify-start border-b border-border pb-0">
          <TabsTrigger value="summary">
            Summary
            {resummarizing && (
              <Loader2 className="h-3.5 w-3.5 ml-1.5 animate-spin" />
            )}
          </TabsTrigger>
          {hasTranscript && (
            <TabsTrigger value="transcript">
              Transcript
              <Badge variant="secondary" className="ml-1.5 text-xs">
                {notes.transcript!.length}
              </Badge>
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="summary">
          {resummarizing ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
              <Loader2 className="h-8 w-8 animate-spin" />
              <p className="text-sm font-medium">Regenerating summary...</p>
              {resummarizeProgress && (
                <p className="text-xs">{resummarizeProgress}</p>
              )}
            </div>
          ) : (
            <SummaryTab
              overview={notes.overview}
              keywords={notes.keywords}
              topics={notes.topics}
              decisions={notes.decisions}
              actionItems={notes.action_items}
              questions={notes.questions}
              apply={apply}
            />
          )}
        </TabsContent>

        {hasTranscript && (
          <TabsContent value="transcript">
            <TranscriptTab
              transcript={notes.transcript!}
              apply={apply}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
