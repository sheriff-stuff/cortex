import { useEffect, useRef, useCallback } from 'react';
import type { Job } from '@/types';
import { api } from '@/api';

interface UsePollJobOptions {
  /** Called on each poll with the latest job state. */
  onProgress?: (job: Job) => void;
  /** Called once when the job reaches 'completed'. */
  onComplete?: (job: Job) => void;
  /** Called once when the job reaches 'failed'. */
  onFailed?: (job: Job) => void;
  /** Polling interval in ms. Default: 2000. */
  interval?: number;
}

/**
 * Returns a `startPolling(jobId)` function that polls a job until it
 * completes or fails, then stops automatically. Cleans up on unmount.
 */
export function usePollJob(options: UsePollJobOptions = {}) {
  const { onProgress, onComplete, onFailed, interval = 2000 } = options;
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (jobId: string) => {
      stopPolling();
      timerRef.current = setInterval(async () => {
        try {
          const job = await api.getJob(jobId);
          onProgress?.(job);

          if (job.status === 'completed' || job.status === 'failed') {
            stopPolling();
            if (job.status === 'completed') onComplete?.(job);
            else onFailed?.(job);
          }
        } catch {
          // Keep polling on transient errors
        }
      }, interval);
    },
    [stopPolling, onProgress, onComplete, onFailed, interval],
  );

  // Clean up on unmount
  useEffect(() => stopPolling, [stopPolling]);

  return { startPolling, stopPolling };
}
