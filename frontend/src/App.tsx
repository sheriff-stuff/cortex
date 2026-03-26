import { useState, useCallback } from 'react';
import type { AppState, MeetingNotes } from '@/types';
import { api } from '@/api';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import Layout from '@/components/Layout';
import NotesList from '@/components/NotesList';
import UploadPage from '@/components/UploadPage';
import NotesView from '@/components/NotesView';

export default function App() {
  const [state, setState] = useState<AppState>('home');
  const [notes, setNotes] = useState<MeetingNotes | null>(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  // Bump to force NotesList re-mount after upload
  const [listKey, setListKey] = useState(0);

  const goHome = useCallback(() => {
    setState('home');
    setNotes(null);
    setError('');
    setUploading(false);
    setListKey((k) => k + 1);
  }, []);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError('');
    try {
      await api.upload(file);
      setUploading(false);
      // Go straight to home — NotesList shows job progress inline
      goHome();
    } catch (err) {
      setUploading(false);
      setError(err instanceof Error ? err.message : 'Upload failed');
      setState('error');
    }
  }, [goHome]);

  const handleSelectNote = useCallback(async (filename: string) => {
    try {
      const n = await api.getSavedNotes(filename);
      setNotes(n);
      setState('viewing');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load notes');
      setState('error');
    }
  }, []);

  return (
    <Layout>
      {state === 'home' && (
        <NotesList
          key={listKey}
          onSelect={handleSelectNote}
          onUpload={() => setState('uploading')}
        />
      )}

      {state === 'uploading' && (
        <UploadPage onUpload={handleUpload} uploading={uploading} />
      )}

      {state === 'viewing' && notes && <NotesView notes={notes} onReset={goHome} />}

      {state === 'error' && (
        <div className="text-center py-16">
          <Alert variant="destructive" className="max-w-md mx-auto mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button onClick={goHome}>Back to Home</Button>
        </div>
      )}
    </Layout>
  );
}
