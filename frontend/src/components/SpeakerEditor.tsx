import { useState } from 'react';
import type { SpeakerNameMap } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Users, Pencil, X, ChevronRight } from 'lucide-react';

interface Props {
  speakers: string[];
  speakerNames: SpeakerNameMap;
  onSave: (names: SpeakerNameMap) => void;
}

export default function SpeakerEditor({ speakers, speakerNames, onSave }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<SpeakerNameMap>({});

  function startEditing() {
    setDraft({ ...speakerNames });
    setIsEditing(true);
  }

  function cancel() {
    setIsEditing(false);
    setDraft({});
  }

  function save() {
    onSave(draft);
    setIsEditing(false);
  }

  function updateDraft(label: string, name: string) {
    setDraft((prev) => ({ ...prev, [label]: name }));
  }

  const hasAssignments = speakers.some((s) => speakerNames[s]);

  return (
    <Card>
      <CardHeader
        className="flex flex-row items-center justify-between space-y-0 pb-2 cursor-pointer select-none"
        onClick={() => !isEditing && setIsOpen((o) => !o)}
      >
        <CardTitle className="flex items-center gap-2 text-base">
          <ChevronRight className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
          <Users className="h-4 w-4" />
          Speaker Names
        </CardTitle>
        {isOpen && !isEditing && (
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); startEditing(); }}
            aria-label="Edit speaker names"
          >
            <Pencil className="h-4 w-4" />
          </Button>
        )}
      </CardHeader>
      {isOpen && <CardContent>
        {isEditing ? (
          <div className="space-y-3">
            {speakers.map((label) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground w-24 shrink-0">{label}</span>
                <input
                  type="text"
                  value={draft[label] || ''}
                  onChange={(e) => updateDraft(label, e.target.value)}
                  placeholder="Enter name"
                  className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  aria-label={`Name for ${label}`}
                />
              </div>
            ))}
            <div className="flex gap-2 pt-1">
              <Button size="sm" onClick={save}>Save</Button>
              <Button size="sm" variant="outline" onClick={cancel}>
                <X className="h-3 w-3 mr-1" />
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            {speakers.map((label) => (
              <div key={label} className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">{label}:</span>
                {speakerNames[label] ? (
                  <span>{speakerNames[label]}</span>
                ) : (
                  <span className="text-muted-foreground/50 italic">Not assigned</span>
                )}
              </div>
            ))}
            {!hasAssignments && (
              <p className="text-sm text-muted-foreground/60 pt-1">
                Click the edit button to assign names to speakers.
              </p>
            )}
          </div>
        )}
      </CardContent>}
    </Card>
  );
}
