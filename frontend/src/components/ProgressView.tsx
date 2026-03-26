import type { Job } from '@/types';
import { Loader2 } from 'lucide-react';

export default function ProgressView({ job }: { job: Job }) {
  return (
    <div className="flex flex-col items-center gap-6 py-16">
      <h2 className="text-[22px] font-semibold">Processing your meeting...</h2>
      <div className="flex items-center gap-3 text-base">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        <span>{job.progress}</span>
      </div>
      {job.source_filename && (
        <div className="text-sm text-muted-foreground">{job.source_filename}</div>
      )}
    </div>
  );
}
