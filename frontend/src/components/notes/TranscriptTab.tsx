import type { TranscriptSegment } from '@/types';
import SpeakerAvatar from '@/components/SpeakerAvatar';

interface TranscriptGroup {
  speaker: string;
  displayName: string;
  startTimestamp: string;
  segments: TranscriptSegment[];
}

function groupSegments(
  transcript: TranscriptSegment[],
  apply: (text: string) => string,
): TranscriptGroup[] {
  const groups: TranscriptGroup[] = [];
  for (const seg of transcript) {
    const prev = groups[groups.length - 1];
    if (prev && prev.speaker === seg.speaker) {
      prev.segments.push(seg);
    } else {
      groups.push({
        speaker: seg.speaker,
        displayName: apply(seg.speaker),
        startTimestamp: seg.timestamp,
        segments: [seg],
      });
    }
  }
  return groups;
}

interface Props {
  transcript: TranscriptSegment[];
  apply: (text: string) => string;
}

export default function TranscriptTab({ transcript, apply }: Props) {
  const groups = groupSegments(transcript, apply);

  if (groups.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No transcript available.
      </p>
    );
  }

  return (
    <div className="pt-4">
      {groups.map((group, i) => (
        <div
          key={i}
          className="flex gap-3 py-4 border-b border-border last:border-b-0"
        >
          <SpeakerAvatar name={group.displayName} />
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2 mb-1">
              <span className="font-semibold text-sm">{group.displayName}</span>
              <span className="text-xs text-muted-foreground font-mono">
                {group.startTimestamp}
              </span>
            </div>
            <div className="space-y-1">
              {group.segments.map((seg, j) => (
                <p key={j} className="text-sm leading-relaxed">
                  {j > 0 && group.segments.length > 1 && (
                    <span className="text-xs text-muted-foreground font-mono mr-2">
                      {seg.timestamp}
                    </span>
                  )}
                  {apply(seg.text)}
                </p>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
