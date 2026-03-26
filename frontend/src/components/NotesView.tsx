import { Fragment, useCallback, useEffect, useState } from 'react';
import type { MeetingNotes, SpeakerNameMap } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, CheckCircle, Square, HelpCircle, MessageCircle, AlertCircle, ChevronRight, FileText } from 'lucide-react';
import SpeakerEditor from '@/components/SpeakerEditor';
import { extractSpeakers, applySpeakerNames } from '@/utils';
import { api } from '@/api';

interface Props {
  notes: MeetingNotes;
  onReset: () => void;
}

export default function NotesView({ notes, onReset }: Props) {
  const { metadata } = notes;
  const [speakerNames, setSpeakerNames] = useState<SpeakerNameMap>(
    () => notes.speaker_names ?? {},
  );
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const speakers = extractSpeakers(notes);
  const apply = (text: string) => applySpeakerNames(text, speakerNames);

  useEffect(() => {
    setSpeakerNames(notes.speaker_names ?? {});
  }, [notes.filename, notes.speaker_names]);

  const handleSave = useCallback(
    async (names: SpeakerNameMap) => {
      setSpeakerNames(names);
      try {
        const saved = await api.saveSpeakers(notes.filename, names);
        setSpeakerNames(saved);
      } catch {
        // Keep local state even if save fails
      }
    },
    [notes.filename],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Meeting Notes &mdash; {metadata.meeting_date}</h1>
          <div className="flex flex-wrap gap-2 mt-2">
            <Badge variant="secondary">Duration: {metadata.duration}</Badge>
            <Badge variant="secondary">Speakers: {metadata.speakers}</Badge>
            {metadata.meeting_time && (
              <Badge variant="secondary">Time: {metadata.meeting_time}</Badge>
            )}
          </div>
        </div>
        <Button variant="outline" onClick={onReset}>
          <ArrowLeft className="h-4 w-4" />
          All Notes
        </Button>
      </div>

      {speakers.length > 0 && (
        <SpeakerEditor
          speakers={speakers}
          speakerNames={speakerNames}
          onSave={handleSave}
        />
      )}

      {/* Topics */}
      {notes.topics.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Key Topics Discussed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {notes.topics.map((t, i) => (
              <div key={i}>
                <div className="font-semibold">
                  {i + 1}. {t.title}
                </div>
                <div className="text-sm text-muted-foreground mt-0.5">{apply(t.description)}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Decisions */}
      {notes.decisions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Decisions Made</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {notes.decisions.map((d, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <CheckCircle className="h-5 w-5 text-success mt-0.5 shrink-0" />
                  <div>
                    <div>{d.decision}</div>
                    {d.detail && <div className="text-sm text-muted-foreground mt-0.5">{apply(d.detail)}</div>}
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Action Items */}
      {notes.action_items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Action Items</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {notes.action_items.map((a, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <Square className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                  <div>
                    <div>{a.task}</div>
                    {a.detail && <div className="text-sm text-muted-foreground mt-0.5">{apply(a.detail)}</div>}
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Questions & Answers */}
      {notes.questions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Questions & Answers</CardTitle>
          </CardHeader>
          <CardContent>
            {notes.questions.map((q, i) => (
              <Fragment key={i}>
                {i > 0 && <Separator className="my-4" />}
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <HelpCircle className="h-5 w-5 text-warning mt-0.5 shrink-0" />
                    <div>
                      <div className="font-medium">{q.question}</div>
                      {q.attribution && (
                        <div className="text-sm text-muted-foreground mt-0.5">{apply(q.attribution)}</div>
                      )}
                    </div>
                  </div>
                  {q.answer ? (
                    <div className="flex items-start gap-2 ml-7">
                      <MessageCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                      <div>
                        <div className="text-sm">{apply(q.answer)}</div>
                        {q.answer_attribution && (
                          <div className="text-sm text-muted-foreground mt-0.5">{apply(q.answer_attribution)}</div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 ml-7">
                      <AlertCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm text-muted-foreground italic">Unanswered</span>
                    </div>
                  )}
                </div>
              </Fragment>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Transcript */}
      {notes.transcript && notes.transcript.length > 0 && (
        <Card>
          <CardHeader
            className="cursor-pointer select-none"
            onClick={() => setTranscriptOpen((o) => !o)}
          >
            <CardTitle className="flex items-center gap-2 text-base">
              <ChevronRight className={`h-4 w-4 transition-transform ${transcriptOpen ? 'rotate-90' : ''}`} />
              <FileText className="h-4 w-4" />
              Full Transcript
              <Badge variant="secondary" className="ml-1">{notes.transcript.length} segments</Badge>
            </CardTitle>
          </CardHeader>
          {transcriptOpen && (
            <CardContent className="space-y-3">
              {notes.transcript.map((seg, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="text-xs text-muted-foreground font-mono mt-0.5 shrink-0">{seg.timestamp}</span>
                  <div>
                    <span className="font-semibold text-sm">{apply(seg.speaker)}:</span>{' '}
                    <span className="text-sm">{apply(seg.text)}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
