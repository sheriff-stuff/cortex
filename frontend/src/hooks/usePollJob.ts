import { useEffect, useRef, useCallback } from 'react';
import type { Job } from '@/types';

interface UsePollJobOptions {
  /** Called on each progress event with the latest job state. */
  onProgress?: (job: Job) => void;
  /** Called once when the job reaches 'completed'. */
  onComplete?: (job: Job) => void;
  /** Called once when the job reaches 'failed'. */
  onFailed?: (job: Job) => void;
}

/**
 * Returns a `startPolling(jobId)` function that opens an SSE connection
 * to the job events endpoint and fires callbacks on progress/completion.
 * Cleans up on unmount.
 */
export function usePollJob(options: UsePollJobOptions = {}) {
  const { onProgress, onComplete, onFailed } = options;
  const esRef = useRef<EventSource | null>(null);

  const stopPolling = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (jobId: string) => {
      stopPolling();
      const es = new EventSource(`/jobs/${jobId}/events`);
      esRef.current = es;

      es.addEventListener('status', (e: MessageEvent) => {
        const colonIdx = e.data.indexOf(': ');
        const status = (colonIdx >= 0 ? e.data.slice(0, colonIdx) : e.data) as Job['status'];
        const progress = colonIdx >= 0 ? e.data.slice(colonIdx + 2) : '';
        onProgress?.({ job_id: jobId, status, progress, source_filename: '' });
      });

      es.addEventListener('progress', (e: MessageEvent) => {
        onProgress?.({ job_id: jobId, status: 'processing', progress: e.data, source_filename: '' });
      });

      es.addEventListener('done', (e: MessageEvent) => {
        const status = e.data as Job['status'];
        const job: Job = { job_id: jobId, status, progress: 'Complete', source_filename: '' };
        if (status === 'completed') onComplete?.(job);
        else onFailed?.(job);
        stopPolling();
      });

      es.onerror = () => {
        // Connection lost — notify caller so UI can recover/retry
        const job: Job = {
          job_id: jobId,
          status: 'failed',
          progress: 'Connection error',
          source_filename: '',
        };
        onFailed?.(job);
        stopPolling();
      };
    },
    [stopPolling, onProgress, onComplete, onFailed],
  );

  // Clean up on unmount
  useEffect(() => stopPolling, [stopPolling]);

  return { startPolling, stopPolling };
}
