import { useState } from 'react';
import type { SpeakerNameMap } from '@/types';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import { Users, Pencil, X, ChevronRight } from 'lucide-react';

interface Props {
  speakers: string[];
  speakerNames: SpeakerNameMap;
  onSave: (names: SpeakerNameMap) => void;
}

export default function SpeakerEditor({ speakers, speakerNames, onSave }: Props) {
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
    <Collapsible>
      <div className="flex items-center justify-between">
        <CollapsibleTrigger className="flex items-center gap-2 py-2 cursor-pointer hover:bg-muted/50 rounded-md px-2 -mx-2 transition-colors group text-sm font-medium">
          <ChevronRight className="h-4 w-4 shrink-0 transition-transform group-data-[panel-open]:rotate-90" />
          <Users className="h-4 w-4" />
          Speaker Names
        </CollapsibleTrigger>
        {!isEditing && (
          <Button
            variant="ghost"
            size="xs"
            onClick={startEditing}
            aria-label="Edit speaker names"
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
      <CollapsibleContent>
        <div className="pl-8 pt-1 pb-2">
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
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
